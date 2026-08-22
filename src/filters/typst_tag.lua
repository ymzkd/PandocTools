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
--
-- 右寄せの実現方法:
--   当初は "$ BODY #h(1fr) "(番号)" $" としていたが、Typst のブロック数式は
--   内容幅にフィットして中央寄せされるため、#h(1fr) が数式ボックス内で閉じ、
--   番号が数式のすぐ右に留まって本文右端まで届かなかった。
--   そこで math.equation の numbering 機能で Typst 標準の数式番号レイアウト
--   (数式は本文中央・番号は本文右端) を使う。
--
-- 適用範囲: TypstAdapter からのみ。LaTeX 経路では \tag がそのまま機能するため不要。

function Math(el)
  if el.mathtype ~= "DisplayMath" then
    return nil
  end

  local tag = el.text:match("\\tag%s*{(.-)}")
  if not tag or tag == "" then
    -- タグ無し / 空タグは pandoc 既定処理に委ねる
    return nil
  end

  -- \tag{...} を数式本体から除去 (\label は typst writer がラベル化するので残す)
  local body = el.text:gsub("\\tag%s*{.-}", "")

  -- 残った数式を pandoc 自身に typst へ変換させる (LaTeX→typst 変換を流用)
  local doc = pandoc.Pandoc({ pandoc.Para({ pandoc.Math(pandoc.DisplayMath, body) }) })
  local typst = pandoc.write(doc, "typst"):gsub("%s+$", "")

  -- "$ BODY $" の BODY を取り出す
  -- 末尾には \label 由来の Typst ラベル (<eq:x>) が付くことがあるので suffix として温存する。
  -- ここを "$" 終端固定にすると label 付きの式がマッチせず、tag が捨てられて番号が消える。
  local inner, suffix = typst:match("^%$%s(.-)%s%$(.*)$")
  if not inner then
    -- 想定外の形式: 番号は欠けるが変換自体は通る既定処理に委ねる
    return nil
  end

  -- tag に LaTeX 記法 (\ast 等) が含まれるときは数式として組む。
  -- 文字列リテラルのままだと "\ast" がそのまま印字されてしまう。
  local numbering
  if tag:find("\\", 1, true) then
    local tag_doc = pandoc.Pandoc({ pandoc.Para({ pandoc.Math(pandoc.InlineMath, tag) }) })
    local tag_typst = pandoc.write(tag_doc, "typst"):gsub("%s+$", "")
    -- ] を含むと content ブロックが途中で閉じてしまうので、その場合は文字列側に委ねる
    if not tag_typst:find("]", 1, true) then
      numbering = '_ => [(' .. tag_typst .. ')]'
    end
  end
  if not numbering then
    -- Typst 文字列リテラルへ埋め込むため \ と " をエスケープ
    local tag_str = tag:gsub("\\", "\\\\"):gsub('"', '\\"')
    numbering = '_ => "(' .. tag_str .. ')"'
  end

  -- math.equation を直接構築し、番号付けをこの数式だけに与える。
  -- numbering 関数は Typst のカウンタ値を無視して原文 tag を固定表示する。
  -- コンテンツブロック (#[#set ...]) で包む方式は使えない。pandoc-crossref 由来の
  -- ラベルが数式ではなく styled 要素に付いてしまい、Typst が参照時に
  -- "cannot reference styled" で失敗するため。
  local out = '#math.equation(block: true, numbering: ' .. numbering
    .. ', $ ' .. inner .. ' $)' .. suffix
  return pandoc.RawInline("typst", out)
end
