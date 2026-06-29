// =====================================================================
// Pandoc → Typst カスタムテンプレート (日本語対応)
//   pandoc --template=... 用 の完全テンプレート
// Reference: HAKO/_TEMP/TMP_Typst/sample_typst/main.typ
// =====================================================================

#import "@preview/js:0.1.3": js, maketitle

// --------------------------------------------------------------------
// グローバル設定 (terms/table/figure)
// --------------------------------------------------------------------

#let horizontalrule = line(start: (25%, 0%), end: (75%, 0%))

#show terms: it => {
  it.children
    .map(child => [
      #strong[#child.term]
      #block(inset: (left: 1.5em, top: -0.4em))[#child.description]
    ])
    .join()
}

#set table(
  inset: 6pt,
  stroke: 0.5pt,
)

#show figure.where(kind: table): set figure.caption(position: $if(table-caption-position)$$table-caption-position$$else$top$endif$)

#show figure.where(kind: image): set figure.caption(position: $if(figure-caption-position)$$figure-caption-position$$else$bottom$endif$)

// --------------------------------------------------------------------
// conf : Pandoc の本文ラッパに対応するエントリポイント
// --------------------------------------------------------------------

#let conf(
  title: none,
  subtitle: none,
  authors: (),
  keywords: (),
  date: none,
  lang: "ja",
  region: "JP",
  abstract-title: none,
  abstract: none,
  thanks: none,
  margin: (top: 30mm, bottom: 25mm, left: 25mm, right: 25mm),
  // 個別マージン (Pandoc 変数 margin-top 等で上書き、設定があれば margin より優先)
  margin-top: none,
  margin-bottom: none,
  margin-left: none,
  margin-right: none,
  paper: "a4",
  font: none,
  fontsize: 10pt,
  mathfont: none,
  codefont: none,
  // CJK フォント (Pandoc 変数 cjk-mainfont / cjk-sansfont で上書き)。
  // 既定 none のときは js.with() へ渡さず、js パッケージ既定 (原ノ味) に委ねる。
  cjk-mainfont: none,
  cjk-sansfont: none,
  linestretch: 1.0,
  sectionnumbering: none,
  pagenumbering: "1 / 1",
  linkcolor: none,
  citecolor: none,
  filecolor: none,
  cols: 1,
  doc,
) = {
  // 和文フォントは未指定 (none) のとき js.with() へ渡さず、js パッケージ既定
  // (Harano Aji Mincho / Harano Aji Gothic = 原ノ味) をそのまま使わせる。
  // Pandoc 変数 cjk-mainfont / cjk-sansfont が指定された場合のみ上書きする。
  let cjk-fonts = (:)
  if cjk-mainfont != none { cjk-fonts.insert("seriffont-cjk", cjk-mainfont) }
  if cjk-sansfont != none { cjk-fonts.insert("sansfont-cjk", cjk-sansfont) }

  // jsarticle 風レイアウト (欧文フォントは fallback まで含めて指定)
  show: js.with(
    lang: lang,
    paper: paper,
    fontsize: fontsize,
    seriffont: if font != none { font.at(0, default: "New Computer Modern") } else { "New Computer Modern" },
    sansfont: if font != none { font.at(0, default: "Source Sans Pro") } else { "Source Sans Pro" },
    ..cjk-fonts,
  )

  // 個別マージン指定があれば margin に反映
  let final-margin = (
    top: if margin-top != none { margin-top } else { margin.at("top", default: 30mm) },
    bottom: if margin-bottom != none { margin-bottom } else { margin.at("bottom", default: 25mm) },
    left: if margin-left != none { margin-left } else { margin.at("left", default: 25mm) },
    right: if margin-right != none { margin-right } else { margin.at("right", default: 25mm) },
  )

  // 余白とページ番号 (js の自動ヘッダは無効化)
  set page(
    margin: final-margin,
    header: none,
    numbering: pagenumbering,
  )

  if sectionnumbering != none {
    set heading(numbering: sectionnumbering)
  }

  set math.equation(numbering: none)
  set par(leading: 0.65em * linestretch)

  if title != none {
    let author-str = if type(authors) == array and authors.len() > 0 {
      authors
        .map(a => if type(a) == dictionary { a.at("name", default: "") } else { a })
        .join(" / ")
    } else { "" }

    maketitle(
      title: title,
      authors: author-str,
    )
  }

  doc
}

$if(smart)$
$else$
#set smartquote(enabled: false)

$endif$
$for(header-includes)$
$header-includes$

$endfor$
#show: doc => conf(
$if(title)$
  title: [$title$],
$endif$
$if(subtitle)$
  subtitle: [$subtitle$],
$endif$
$if(author)$
  authors: (
$for(author)$
$if(author.name)$
    ( name: [$author.name$],
      affiliation: [$author.affiliation$],
      email: [$author.email$] ),
$else$
    ( name: [$author$],
      affiliation: "",
      email: "" ),
$endif$
$endfor$
    ),
$endif$
$if(keywords)$
  keywords: ($for(keywords)$"$keywords$"$sep$, $endfor$),
$endif$
$if(date)$
  date: [$date$],
$endif$
$if(lang)$
  lang: "$lang$",
$endif$
$if(region)$
  region: "$region$",
$endif$
$if(abstract-title)$
  abstract-title: [$abstract-title$],
$endif$
$if(abstract)$
  abstract: [$abstract$],
$endif$
$if(thanks)$
  thanks: [$thanks$],
$endif$
$if(margin)$
  margin: ($for(margin/pairs)$$margin.key$: $margin.value$,$endfor$),
$endif$
$if(papersize)$
  paper: "$papersize$",
$endif$
$if(mainfont)$
  font: ("$mainfont$",),
$endif$
$if(fontsize)$
  fontsize: $fontsize$,
$endif$
$if(mathfont)$
  mathfont: ($for(mathfont)$"$mathfont$",$endfor$),
$endif$
$if(codefont)$
  codefont: ($for(codefont)$"$codefont$",$endfor$),
$endif$
$if(cjk-mainfont)$
  cjk-mainfont: "$cjk-mainfont$",
$endif$
$if(cjk-sansfont)$
  cjk-sansfont: "$cjk-sansfont$",
$endif$
$if(margin-top)$
  margin-top: $margin-top$,
$endif$
$if(margin-bottom)$
  margin-bottom: $margin-bottom$,
$endif$
$if(margin-left)$
  margin-left: $margin-left$,
$endif$
$if(margin-right)$
  margin-right: $margin-right$,
$endif$
$if(linestretch)$
  linestretch: $linestretch$,
$endif$
$if(section-numbering)$
  sectionnumbering: "$section-numbering$",
$endif$
  pagenumbering: $if(page-numbering)$"$page-numbering$"$else$"1 / 1"$endif$,
$if(linkcolor)$
  linkcolor: [$linkcolor$],
$endif$
$if(citecolor)$
  citecolor: [$citecolor$],
$endif$
$if(filecolor)$
  filecolor: [$filecolor$],
$endif$
  cols: $if(columns)$$columns$$else$1$endif$,
  doc,
)

$for(include-before)$
$include-before$

$endfor$
$if(toc)$
#outline(
  title: auto$if(toc-depth)$,
  depth: $toc-depth$$endif$
);
$endif$

$body$

$if(citations)$
$for(nocite-ids)$
#cite(label("$it$"), form: none)
$endfor$
$if(csl)$

#set bibliography(style: "$csl$")
$elseif(bibliographystyle)$

#set bibliography(style: "$bibliographystyle$")
$endif$
$if(bibliography)$

#bibliography($for(bibliography)$"$bibliography$"$sep$,$endfor$$if(full-bibliography)$, full: true$endif$)
$endif$
$endif$
$for(include-after)$

$include-after$
$endfor$
