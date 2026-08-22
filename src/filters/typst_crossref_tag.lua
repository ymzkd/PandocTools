-- typst 出力時、pandoc-crossref の式番号を LaTeX 経路と同じ結果に揃える。
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
-- 方針:
--   pass 1: {#eq:...} 付き数式を文書順に走査し、
--     - \tag{T} を持つ  -> ラベルの表示番号は T。crossref の \qquad{...} は除去
--     - \tag を持たない -> tag 無し数式だけを 1 から数えた番号 N を割り当て、
--                          \qquad{...} を \tag{N} に置き換える
--     いずれも番号の描画は typst_tag.lua に任せる。これで tag の有無に関わらず
--     番号が本文右端に揃い、LaTeX 経路と同じ採番になる。
--   pass 2: crossref が生成した参照リンクの表示テキストを pass 1 の番号に差し替える。
--   pass 3: crossref が圧縮した範囲参照 (eqns. 6-8) を明示列挙へ展開する。
--           番号を振り直すと連続性が崩れ、範囲表記が実際の集合と食い違うため。
--
-- 参照の特定方法:
--   TypstAdapter は crossref 実行時に linkReferences=true を渡す。これにより
--   参照が Link (target = "#eq:...") として出力されるため、番号のテキストを
--   位置や書式に頼らず正確に特定できる。副次的に PDF 内リンクとしても機能する。
--
-- 適用順: pandoc-crossref の後、typst_tag.lua の前。
-- 適用範囲: TypstAdapter からのみ。LaTeX 経路では crossref が正しく採番する。

local number_of_label = {}

-- \tag を持たない数式に振る番号 (LaTeX の equation カウンタ相当)
local untagged_count = 0

-- 文書順のラベル一覧と、その並び順 (範囲参照の展開に使う)
local labels_in_order = {}
local order_of_label = {}

-- crossref の範囲参照の区切り (rangeDelim の既定値)
local RANGE_DELIM = "-"

-- crossref が数式末尾に差し込む番号表示 (\qquad{(2)} など) を取り除く
local function strip_crossref_number(text)
  return (text:gsub("%s*\\qquad%s*{.-}%s*$", ""))
end

-- pass 1: {#eq:...} 付き数式の表示番号を決め、typst_tag.lua が読む \tag に集約する
local function assign_numbers(span)
  if not span.identifier:match("^eq:") then
    return nil
  end
  for _, el in ipairs(span.content) do
    if el.t == "Math" and el.mathtype == "DisplayMath" then
      local tag = el.text:match("\\tag%s*{(.-)}")
      if tag and tag ~= "" then
        number_of_label[span.identifier] = tag
        el.text = strip_crossref_number(el.text)
      else
        untagged_count = untagged_count + 1
        local number = tostring(untagged_count)
        number_of_label[span.identifier] = number
        el.text = strip_crossref_number(el.text) .. " \\tag{" .. number .. "}"
      end
      labels_in_order[#labels_in_order + 1] = span.identifier
      order_of_label[span.identifier] = #labels_in_order
    end
  end
  return span
end

-- 番号を表示要素にする。\ast のような LaTeX 記法を含む tag は数式として組む
-- (文字列のままだと "\ast" がそのまま印字される)
local function number_inline(number)
  if number:find("\\", 1, true) then
    return pandoc.Math(pandoc.InlineMath, number)
  end
  return pandoc.Str(number)
end

-- pass 2: 参照リンクの表示テキストを pass 1 で決めた番号に差し替える
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

-- pass 3: crossref が圧縮した範囲参照 (eqns. 6-8) を明示列挙へ展開する
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
  { Span = assign_numbers },
  { Link = renumber_reference },
  { Inlines = expand_ranges },
}
