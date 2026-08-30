-- typst 出力時、式番号を LaTeX 経路と同じ結果に揃える。
--
-- 背景:
--   pandoc-crossref は LaTeX 出力では採番を LaTeX に委譲する (\ref{} を出す) ため、
--   xelatex では以下の挙動になる。
--     - \tag{11} がある数式は "(11)" が出て、参照も "eq. 11"
--     - \tag が無い数式は LaTeX の equation カウンタで採番される。
--       \tag はカウンタを進めないので、tag 付き数式は番号を消費しない
--   一方 typst 出力では委譲先が無いため crossref が自前カウンタの値を埋め込み、
--     - \tag があっても無視されて通し番号になる ("eq. 2" 等)
--     - tag 付き数式もカウンタを消費するので、tag 無し数式の番号がずれる
--     - 数式本体にも \qquad{(2)} が差し込まれ、typst_tag.lua が \tag から
--       復元する番号と二重に表示される
--   という 3 つのずれが生じる。
--
--   さらに -M eq-numbers=true (LaTeX 側は eq_number.lua が equation 環境で包む)
--   のとき、typst には包む先の環境が無い。そこで本フィルタが LaTeX の equation
--   カウンタの挙動そのものを Lua で再現し、番号を \tag へ集約する。
--
-- 方針:
--   pass 1: 本文の DisplayMath を文書順に走査し、番号を \tag{...} へ集約する。
--     - \nonumber を持つ    -> 番号なし。カウンタ非消費 (明示的な抑制)
--     - \tag{T} を持つ      -> 表示番号は T。カウンタ非消費 (LaTeX の \tag と同じ)
--     - align 等の環境      -> 環境が番号を決めるので採番しない。カウンタ非消費
--     - crossref が採番済み -> \qquad{...} を落とし、通し番号を \tag{N} で振り直す
--     - それ以外            -> eq-numbers が有効なときだけ通し番号 \tag{N} を振る
--     いずれも番号の描画は typst_tag.lua に任せる。これで番号が本文右端に揃い、
--     LaTeX 経路と同じ採番になる。
--   pass 2: pass 1 が決めた番号を {#eq:...} ラベルに紐付ける。
--   pass 3: crossref が生成した参照リンクの表示テキストを pass 2 の番号に差し替える。
--   pass 4: crossref が圧縮した範囲参照 (eqns. 6-8) を明示列挙へ展開する。
--           番号を振り直すと連続性が崩れ、範囲表記が実際の集合と食い違うため。
--
-- pass 1 と pass 2 を分ける理由:
--   Lua フィルタの Inline 走査は bottom-up で、Span の中の Math が Span 本体より
--   先に処理される。採番を Span 側で行うと、ラベルの無い素の数式と順序が混ざって
--   文書順の通し番号にならない。そこで採番は Math だけで完結させ (pass 1)、
--   Span は入り終えた \tag を読むだけにしている (pass 2)。
--
-- メタデータを走査しない理由:
--   pandoc-crossref は equationNumberTeX 等の書式定義を大量の DisplayMath として
--   メタデータへ持ち込む。Math を単独のフィルタパスで走らせるとそれらまで
--   採番対象になり番号が飛ぶため、doc.blocks だけを walk する。
--
-- 参照の特定方法:
--   TypstAdapter は crossref 実行時に linkReferences=true を渡す。これにより
--   参照が Link (target = "#eq:...") として出力されるため、番号のテキストを
--   位置や書式に頼らず正確に特定できる。副次的に PDF 内リンクとしても機能する。
--
-- 適用順: pandoc-crossref の後、typst_tag.lua の前。
-- 適用範囲: TypstAdapter からのみ。LaTeX 経路では eq_number.lua と LaTeX が担う。

local number_of_label = {}

-- \tag / \nonumber を持たない数式に振る番号 (LaTeX の equation カウンタ相当)
local untagged_count = 0

-- 文書順のラベル一覧と、その並び順 (範囲参照の展開に使う)
local labels_in_order = {}
local order_of_label = {}

-- -M eq-numbers=true のとき、ラベルの無い素の数式にも通し番号を振る
local eq_numbers = false

-- crossref の範囲参照の区切り (rangeDelim の既定値)
local RANGE_DELIM = "-"

-- -M eq-numbers=true / -M eq-numbers のどちらでも受け取れるようにする
local function meta_flag(meta, key)
  local value = meta[key]
  if value == nil then
    return false
  end
  if type(value) == "boolean" then
    return value
  end
  local text = pandoc.utils.stringify(value)
  return text == "true" or text == "yes" or text == "1"
end

-- crossref が数式末尾に差し込む番号表示 (\qquad{(2)} など) を取り除く
local function strip_crossref_number(text)
  return (text:gsub("%s*\\qquad%s*{.-}%s*$", ""))
end

-- crossref がこの数式を採番済みか (= {#eq:...} ラベルが付いている)
local function is_crossref_numbered(text)
  return text:find("\\qquad%s*{.-}%s*$") ~= nil
end

-- 自前で式番号を持つ (もしくは明示的に番号を捨てる) 数式環境。
-- aligned / gathered / split / cases / pmatrix などは display 数式の *内部* 環境で
-- 番号を持たないため、ここには入れない。
-- eq_number.lua の同名リストと対になっている。両者を揃えること。
local NUMBERED_ENVIRONMENTS = {
  equation = true,
  align = true,
  alignat = true,
  flalign = true,
  gather = true,
  multline = true,
  eqnarray = true,
}

-- LaTeX 側 (eq_number.lua) が equation で包まない式と同じ条件。
-- こちらでも採番から外すことで、通し番号の消費が両エンジンで一致する。
-- なお align 等の中身は LaTeX なら行ごとに採番されるが typst writer は環境を
-- 剥がして 1 つの数式にするため、番号の見え方までは揃わない (既知の制約)。
local function has_numbered_environment(text)
  for name in text:gmatch("\\begin%s*{(%a+)%*?}") do
    if NUMBERED_ENVIRONMENTS[name] then
      return true
    end
  end
  return false
end

-- pass 1: 本文の DisplayMath を文書順に走査し、表示番号を \tag へ集約する
local function assign_number(el)
  if el.mathtype ~= "DisplayMath" then
    return nil
  end
  local text = el.text

  -- \nonumber は明示的な番号抑制。crossref が付けた番号も落とす。
  -- typst writer は \nonumber を受け付けて黙って捨てるが、typst_tag.lua が
  -- 数式本体を組み直す経路もあるのでここで取り除いておく。
  if text:find("\\nonumber", 1, true) then
    el.text = strip_crossref_number(text):gsub("\\nonumber%s*", "")
    return el
  end

  local tag = text:match("\\tag%s*{(.-)}")
  if tag and tag ~= "" then
    -- 原文の番号を優先し、通し番号は消費しない (LaTeX の \tag と同じ挙動)
    el.text = strip_crossref_number(text)
    return el
  end

  if has_numbered_environment(text) then
    -- 環境が番号を決めるので通し番号は割り当てない。crossref がラベル付き式に
    -- 差し込んだ番号だけは二重表示を避けるため落とす。
    if is_crossref_numbered(text) then
      el.text = strip_crossref_number(text)
      return el
    end
    return nil
  end

  if is_crossref_numbered(text) or eq_numbers then
    untagged_count = untagged_count + 1
    el.text = strip_crossref_number(text) .. " \\tag{" .. tostring(untagged_count) .. "}"
    return el
  end

  return nil
end

-- pass 2: pass 1 が入れた \tag を {#eq:...} ラベルに紐付ける
local function record_label(span)
  if not span.identifier:match("^eq:") then
    return nil
  end
  for _, el in ipairs(span.content) do
    if el.t == "Math" and el.mathtype == "DisplayMath" then
      local tag = el.text:match("\\tag%s*{(.-)}")
      if tag and tag ~= "" then
        number_of_label[span.identifier] = tag
        labels_in_order[#labels_in_order + 1] = span.identifier
        order_of_label[span.identifier] = #labels_in_order
      end
    end
  end
  return nil
end

local function collect_numbers(doc)
  eq_numbers = meta_flag(doc.meta, "eq-numbers")
  doc.blocks = doc.blocks:walk({ Math = assign_number })
  doc.blocks:walk({ Span = record_label })
  return doc
end

-- 番号を表示要素にする。\ast のような LaTeX 記法を含む tag は数式として組む
-- (文字列のままだと "\ast" がそのまま印字される)
local function number_inline(number)
  if number:find("\\", 1, true) then
    return pandoc.Math(pandoc.InlineMath, number)
  end
  return pandoc.Str(number)
end

-- pass 3: 参照リンクの表示テキストを pass 2 で決めた番号に差し替える
local function renumber_reference(link)
  local label = link.target:match("^#(.+)$")
  if not label then
    return nil
  end
  local number = number_of_label[label]
  if not number then
    return nil
  end
  -- 先頭の番号テキストだけを差し替える。範囲参照 ([@eq:a -@eq:b]) では
  -- リンクの中に別のリンクが入れ子になるため、丸ごと置き換えると内側を失う。
  if link.content[1] == nil or link.content[1].t ~= "Str" then
    return nil
  end
  link.content[1] = number_inline(number)
  return link
end

-- リンクが数式参照ならそのラベルを返す
local function equation_label(el)
  if el.t ~= "Link" then
    return nil
  end
  local label = el.target:match("^#(.+)$")
  if label and number_of_label[label] then
    return label
  end
  return nil
end

-- pass 4: crossref が圧縮した範囲参照 (eqns. 6-8) を明示列挙へ展開する
--
-- crossref は自前カウンタの番号が連続していれば範囲にまとめ、中間の参照を
-- 出力から落とす。pass 1 で番号を振り直すと連続性が崩れるため、範囲表記のまま
-- では実際の集合と食い違う (例: 1, 99, 2 が "1-2" に見えてしまう)。
-- 採番を LaTeX に委譲する xelatex では範囲圧縮が起きないので、展開すると
-- 両エンジンの出力も揃う。
local function expand_ranges(inlines)
  local out = pandoc.Inlines({})
  local i = 1
  while i <= #inlines do
    local first = equation_label(inlines[i])
    local delim = inlines[i + 1]
    local last = inlines[i + 2] and equation_label(inlines[i + 2]) or nil
    local is_range = first and last and delim and delim.t == "Str"
      and delim.text == RANGE_DELIM
      and order_of_label[first] and order_of_label[last]

    if is_range then
      for k = order_of_label[first], order_of_label[last] do
        local label = labels_in_order[k]
        if k > order_of_label[first] then
          out:insert(pandoc.Str(","))
          out:insert(pandoc.Space())
        end
        out:insert(pandoc.Link(
          { number_inline(number_of_label[label]) },
          "#" .. label,
          inlines[i].title,
          inlines[i].attr
        ))
      end
      i = i + 3
    else
      out:insert(inlines[i])
      i = i + 1
    end
  end
  return out
end

return {
  { Pandoc = collect_numbers },
  { Link = renumber_reference },
  { Inlines = expand_ranges },
}
