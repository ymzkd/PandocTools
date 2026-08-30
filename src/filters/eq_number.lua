-- LaTeX 出力で display 数式に通し番号を振る。
--
-- 背景:
--   pandoc は $$...$$ を \[...\] へ落とすため amsmath の無番号 display になり、
--   式番号が出ない。番号を出すには equation 環境で包む必要がある。
--
-- 方針:
--   -M eq-numbers=true のとき、番号を振るべき DisplayMath を
--   \begin{equation}...\end{equation} で包む。採番そのものは LaTeX の equation
--   カウンタに委ねる (typst 側は採番先が無いので typst_crossref_tag.lua が
--   このカウンタの挙動を Lua で再現する)。
--
--   包まないもの (いずれも \[...\] のまま = 無番号・カウンタ非消費):
--     - \nonumber を含む式。利用者が明示的に番号を抑制したもの
--     - \tag{...} を含む式。原文の番号を優先する。LaTeX の \tag も equation
--       カウンタを進めないため、tag 付き式は通し番号を消費しない
--     - 数式環境 (align 等) を含む式。環境が自前で採番するので二重に包まない。
--       default_filter.lua が先に RawInline へ畳むため通常ここへは来ない
--
--   pandoc-crossref がラベル ({#eq:...}) を処理した式は、LaTeX writer 向けには
--   既に RawInline("latex") の equation 環境へ畳まれており Math フィルタには
--   現れない。二重に包む心配はなく、番号も同じ equation カウンタで通る。
--
-- メタデータを走査しない理由:
--   pandoc-crossref は equationNumberTeX 等の書式定義を大量の DisplayMath として
--   メタデータへ持ち込む。Math を単独のフィルタパスで走らせるとそれらまで
--   equation で包んでしまうため、Pandoc フィルタで doc.blocks だけを walk する。
--
-- 適用順: pandoc-crossref の後。
-- 適用範囲: LatexAdapter からのみ。

local enabled = false

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

-- 自前で式番号を持つ (もしくは明示的に番号を捨てる) 数式環境。
-- aligned / gathered / split / cases / pmatrix などは display 数式の *内部* 環境で
-- 番号を持たないため、ここには入れない。入れてしまうと \[\begin{aligned}...\]
-- のような普通の複数行数式が丸ごと無番号になる。
-- typst_crossref_tag.lua の同名リストと対になっている。両者を揃えること。
local NUMBERED_ENVIRONMENTS = {
  equation = true,
  align = true,
  alignat = true,
  flalign = true,
  gather = true,
  multline = true,
  eqnarray = true,
}

-- align / gather / equation* などの「番号を自分で決める環境」を含むか。
-- 環境名だけを取り出して照合するので equation* 等のアスタリスク版も含む
-- (アスタリスク版は無番号を意図しているので、やはり包んではいけない)。
local function has_numbered_environment(text)
  for name in text:gmatch("\\begin%s*{(%a+)%*?}") do
    if NUMBERED_ENVIRONMENTS[name] then
      return true
    end
  end
  return false
end

local function number_math(el)
  if el.mathtype ~= "DisplayMath" then
    return nil
  end
  local text = el.text

  -- \nonumber は amsmath では複数行環境用のコマンドで、\[...\] の中に残ると
  -- エラーになる。\[...\] 自体が無番号なので、取り除くだけで意図どおりになる。
  if text:find("\\nonumber", 1, true) then
    el.text = text:gsub("\\nonumber%s*", "")
    return el
  end

  if not enabled then
    return nil
  end
  if text:find("\\tag", 1, true) or has_numbered_environment(text) then
    return nil
  end
  return pandoc.RawInline("latex", "\\begin{equation}" .. text .. "\\end{equation}")
end

function Pandoc(doc)
  enabled = meta_flag(doc.meta, "eq-numbers")
  doc.blocks = doc.blocks:walk({ Math = number_math })
  return doc
end
