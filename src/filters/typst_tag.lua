-- typst 出力時に LaTeX display 数式の \tag{...} を右寄せの式番号として復元する。
--
-- 背景:
--   pandoc の typst writer は display 数式中の \tag{...} を黙って捨ててしまう。
--   そのため LaTeX (xelatex) では出る式番号 (例: (2.138)) が typst では消える。
--   原文の式番号を保持するため、本フィルタで番号を右寄せで補完する。
--
-- 方針:
--   1. DisplayMath から \tag{...} を取り除いた本体を pandoc に typst へ変換させる
--   2. 得られた "$ BODY $" を math.equation として組み直し、番号を本文右端へ配置する
--   3. 複数行にタグがある場合は equate の行番号機能へ原文タグを渡す。
--      equate は対象の式だけに適用し、初回は Typst がパッケージを自動取得する。
--
-- 右寄せの実現方法:
--   当初は "$ BODY #h(1fr) "(番号)" $" としていたが、Typst のブロック数式は
--   内容幅にフィットして中央寄せされるため、#h(1fr) が数式ボックス内で閉じ、
--   番号が数式のすぐ右に留まって本文右端まで届かなかった。
--   そこで math.equation の numbering 機能で Typst 標準の数式番号レイアウト
--   (数式は本文中央・番号は本文右端) を使う。
--
-- 適用範囲: TypstAdapter からのみ。LaTeX 経路では \tag がそのまま機能するため不要。

local needs_equate = false
local ROW_EQUATION = '#pandoctools-row-equation('

local function strip_comments(text)
  local out, i = {}, 1
  while i <= #text do
    local c = text:sub(i, i)
    if c == '\\' then
      out[#out + 1] = text:sub(i, i + 1)
      i = i + 2
    elseif c == '%' then
      i = text:find('\n', i, true) or (#text + 1)
    else
      out[#out + 1] = c
      i = i + 1
    end
  end
  return table.concat(out)
end

local function convert_math(body)
  -- 残った数式を pandoc 自身に typst へ変換させる (LaTeX→typst 変換を流用)
  local doc = pandoc.Pandoc({ pandoc.Para({ pandoc.Math(pandoc.DisplayMath, body) }) })
  local typst = pandoc.write(doc, "typst"):gsub("%s+$", "")

  -- "$ BODY $" の BODY を取り出す
  -- 末尾には \label 由来の Typst ラベル (<eq:x>) が付くことがあるので suffix として温存する。
  -- ここを "$" 終端固定にすると label 付きの式がマッチせず、tag が捨てられて番号が消える。
  local inner, suffix = typst:match("^%$%s(.-)%s%$(.*)$")
  return inner, suffix
end

local function tag_content(tag)
  -- tag に LaTeX 記法 (\ast 等) が含まれるときは数式として組む。
  -- 文字列リテラルのままだと "\ast" がそのまま印字されてしまう。
  local content
  if tag:find("\\", 1, true) then
    local tag_doc = pandoc.Pandoc({ pandoc.Para({ pandoc.Math(pandoc.InlineMath, tag) }) })
    local tag_typst = pandoc.write(tag_doc, "typst"):gsub("%s+$", "")
    -- ] を含むと content ブロックが途中で閉じてしまうので、その場合は文字列側に委ねる
    if not tag_typst:find("]", 1, true) then
      content = '[(' .. tag_typst .. ')]'
    end
  end
  if not content then
    -- Typst 文字列リテラルへ埋め込むため \ と " をエスケープ
    local tag_str = tag:gsub("\\", "\\\\"):gsub('"', '\\"')
    content = '"(' .. tag_str .. ')"'
  end
  return content
end

-- 外側の整列環境だけを外し、最上位の行区切りを読む。
-- 行列・cases・添字などの内部にある \\ は数式行の区切りではない。
local function split_rows(text)
  local name = text:match('^%s*\\begin%s*{([%a]+%*?)}')
  local row_envs = { align = true, aligned = true, alignat = true,
    alignedat = true, flalign = true, gather = true, gathered = true,
    eqnarray = true }
  if name and row_envs[name:gsub('%*$', '')] then
    text = text:gsub('^%s*\\begin%s*{[%a]+%*?}', '', 1)
      :gsub('\\end%s*{[%a]+%*?}%s*$', '', 1)
    if name:match('at%*?$') then
      text = text:gsub('^%s*%b{}', '', 1)
    end
  end

  local rows, start, i, braces, environments = {}, 1, 1, 0, 0
  while i <= #text do
    local c = text:sub(i, i)
    if c == '%' then
      i = (text:find('\n', i, true) or #text) + 1
    elseif c == '\\' then
      local rest = text:sub(i)
      local env = rest:match('^\\begin%s*{%a+%*?}')
      local ending = rest:match('^\\end%s*{%a+%*?}')
      if env or ending then
        environments = environments + (env and 1 or -1)
        i = i + #(env or ending)
      elseif text:sub(i + 1, i + 1) == '\\' and braces == 0 and environments == 0 then
        rows[#rows + 1] = text:sub(start, i - 1)
        i = i + 2
        -- \\[長さ] の指定は行の内容に含めない。
        local spacing = text:sub(i):match('^%s*%b[]')
        if spacing then i = i + #spacing end
        start = i
      else
        -- \{ / \} はグループの括弧ではない。
        i = i + 2
      end
    else
      if c == '{' then braces = braces + 1 end
      if c == '}' then braces = braces - 1 end
      i = i + 1
    end
  end
  local last = text:sub(start)
  if last:match('%S') then rows[#rows + 1] = last end
  return rows
end

function Math(el)
  if el.mathtype ~= 'DisplayMath' then return nil end
  -- コメント中のタグや行区切りを拾わない。
  local text = strip_comments(el.text)
  local tag_group = text:match('\\tag%s*(%b{})')
  if not tag_group or tag_group == '{}' then return nil end
  local tag = tag_group:sub(2, -2)
  local body, tag_count = text:gsub('\\tag%s*%b{}', '')
  local inner, suffix = convert_math(body)
  if not inner then return nil end

  if tag_count > 1 then
    local rows = split_rows(text)
    local tags = {}
    for _, row in ipairs(rows) do
      local group = row:match('\\tag%s*(%b{})')
      tags[#tags + 1] = group and group ~= '{}' and tag_content(group:sub(2, -2)) or '[]'
    end
    if #rows > 1 then
      needs_equate = true
      -- equate にはネストした equation ではなく数式の body を渡す。
      -- 原文タグのない行は空の content とし、自動番号を追加しない。
      local numbering = '(..nums) => (' .. table.concat(tags, ', ') .. ',).at(nums.pos().at(1, default: 1) - 1)'
      return pandoc.RawInline('typst', ROW_EQUATION
        .. '[#math.equation(block: true, numbering: ' .. numbering
        .. ', ($ ' .. inner .. ' $).body)' .. suffix .. '])')
    end
  end

  local numbering = '_ => ' .. tag_content(tag)

  -- math.equation を直接構築し、番号付けをこの数式だけに与える。
  -- numbering 関数は Typst のカウンタ値を無視して原文 tag を固定表示する。
  -- コンテンツブロック (#[#set ...]) で包む方式は使えない。pandoc-crossref 由来の
  -- ラベルが数式ではなく styled 要素に付いてしまい、Typst が参照時に
  -- "cannot reference styled" で失敗するため。
  local out = '#math.equation(block: true, numbering: ' .. numbering
    .. ', $ ' .. inner .. ' $)' .. suffix
  return pandoc.RawInline("typst", out)
end

function Span(span)
  if span.identifier == '' then return nil end
  for _, el in ipairs(span.content) do
    if el.t == 'RawInline' and el.format == 'typst'
      and el.text:sub(1, #ROW_EQUATION) == ROW_EQUATION then
      -- crossref のラベルをラッパではなく内部の equation に付ける。
      local label = span.identifier:gsub('\\', '\\\\'):gsub('"', '\\"')
      el.text = el.text:sub(1, -2) .. ', id: "' .. label .. '")'
      span.identifier = ''
      return span
    end
  end
end

function Pandoc(doc)
  if needs_equate then
    doc.blocks:insert(1, pandoc.RawBlock('typst', [[
#import "@preview/equate:0.3.2": equate as pandoctools-equate
#let pandoctools-row-equation(eq, id: none) = pandoctools-equate(
  sub-numbering: true,
  breakable: false,
  [#eq#if id != none { label(id) }],
)
]]))
  end
  return doc
end
