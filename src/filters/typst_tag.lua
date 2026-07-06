-- typst 出力時に LaTeX 数式の \tag{...} を右寄せの式番号として復元する。
--
-- 背景:
--   pandoc の typst writer は display 数式中の \tag{...} を黙って捨ててしまう。
--   そのため LaTeX (xelatex) では出る式番号 (例: (2.138)) が typst では消える。
--   原文の式番号を保持するため、本フィルタで番号を右寄せで補完する。
--
-- 方針:
--   1. DisplayMath から \tag{...} を取り除いた本体を pandoc に typst へ変換させる
--   2. 得られた "$ BODY $" を Typst ネイティブの数式番号機能でラップし、番号を
--      本文右端へ右寄せ配置する
--
-- 右寄せの実現方法:
--   当初は "$ BODY #h(1fr) "(番号)" $" としていたが、Typst のブロック数式は
--   内容幅にフィットして中央寄せされるため、#h(1fr) が数式ボックス内で閉じ、
--   番号が数式のすぐ右に留まって本文右端まで届かなかった。
--   そこで #set math.equation(numbering: _ => "(番号)") で Typst 標準の数式番号
--   レイアウト (数式は本文中央・番号は本文右端) を使う。番号カウンタ値は無視し、
--   原文の tag 文字列をそのまま固定表示する。
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

  -- \tag{...} を数式本体から除去
  local body = el.text:gsub("\\tag%s*{.-}", "")

  -- 残った数式を pandoc 自身に typst へ変換させる (LaTeX→typst 変換を流用)
  local doc = pandoc.Pandoc({ pandoc.Para({ pandoc.Math(pandoc.DisplayMath, body) }) })
  local typst = pandoc.write(doc, "typst"):gsub("%s+$", "")

  -- "$ BODY $" の BODY を取り出す
  local inner = typst:match("^%$%s(.-)%s%$$")
  if not inner then
    -- 想定外の形式: 番号は欠けるが変換自体は通る既定処理に委ねる
    return nil
  end

  -- tag を Typst 文字列リテラルへ埋め込むため \ と " をエスケープ
  local tag_str = tag:gsub("\\", "\\\\"):gsub('"', '\\"')

  -- 数式単体をコンテンツブロックで包み、その中だけ数式番号を有効化する。
  -- numbering 関数は番号カウンタを無視して原文 tag を固定表示する。
  local out = '#[#set math.equation(numbering: _ => "(' .. tag_str .. ')")\n$ '
    .. inner .. ' $]'
  return pandoc.RawInline("typst", out)
end
