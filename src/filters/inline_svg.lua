--[[
inline_svg.lua

Markdown 中の SVG を typst / LaTeX どちらの PDF 経路でも図として出力する。

対象:
  1. Markdown に直接書かれた <svg> ... </svg> (raw HTML ブロック / インライン)
  2. 外部 SVG ファイル参照  ![caption](figure.svg)

背景 (どちらも「エラーにならず図だけ消える」ので気付きにくい):
  - raw HTML の <svg> は latex / typst writer が黙って捨てる。
  - ![](x.svg) も pandoc は PDF 埋め込み時に rsvg-convert へ丸投げする実装で、
    未インストールだと警告を出すだけで画像を落とし、終了コードは 0 のままになる。

方針 (engine 別):
  typst : #image("....svg") を RawInline("typst") として直接埋める。
          typst は SVG をネイティブに描画できるので外部ツールは不要。
  latex : SVG を PDF へ変換して Image の src を差し替える。
          変換器は rsvg-convert -> inkscape -> typst の順に自動検出する
          (typst は本アプリの既定エンジンなので通常は必ず存在する)。
  それ以外の出力形式 (html / docx 等) では何もしない。

生成物は内容の SHA1 を名前にしたキャッシュに置くので、何度変換しても増えない。
既定の置き場所は %TEMP%/pandoctools-svg で、PANDOCTOOLS_SVG_DIR で変更できる。
]]

local system = pandoc.system
local utils = pandoc.utils

local IS_TYPST = (FORMAT == "typst")
local IS_LATEX = (FORMAT == "latex" or FORMAT == "beamer")

-- --- ファイル / キャッシュ ---------------------------------------------------

local cached_dir = nil

local function cache_dir()
  if cached_dir then return cached_dir end
  local dir = os.getenv("PANDOCTOOLS_SVG_DIR")
  if not dir or dir == "" then
    local tmp = os.getenv("TMPDIR") or os.getenv("TEMP") or os.getenv("TMP") or "/tmp"
    dir = tmp .. "/pandoctools-svg"
  end
  dir = dir:gsub("\\", "/")
  dir = dir:gsub("/+$", "")
  pcall(system.make_directory, dir, true)
  cached_dir = dir
  return dir
end

local function file_exists(path)
  local f = io.open(path, "rb")
  if f then f:close() return true end
  return false
end

local function read_file(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local contents = f:read("*a")
  f:close()
  return contents
end

local function write_file(path, contents)
  local f = io.open(path, "wb")
  if not f then return false end
  f:write(contents)
  f:close()
  return true
end

local function to_slash(path)
  return (path:gsub("\\", "/"))
end

local function absolute(path)
  local p = to_slash(path)
  if p:match("^%a:/") or p:match("^/") then return p end
  local cwd = to_slash(system.get_working_directory()):gsub("/+$", "")
  return cwd .. "/" .. p
end

-- --- SVG -> PDF 変換 (LaTeX 経路) --------------------------------------------

local function run(cmd, args)
  return (pcall(pandoc.pipe, cmd, args, ""))
end

local converters = {
  function(svg, pdf)
    return run("rsvg-convert", { "-f", "pdf", "-o", pdf, svg })
  end,
  function(svg, pdf)
    return run("inkscape", { "--export-type=pdf", "--export-filename=" .. pdf, svg })
  end,
  function(svg, pdf)
    -- ページを画像ぴったりに切り詰めた .typ を経由して PDF 化する
    local wrapper = svg:gsub("%.svg$", "") .. ".wrap.typ"
    local base = svg:match("[^/]+$")
    local body = "#set page(width: auto, height: auto, margin: 0pt)\n"
      .. '#image("' .. base .. '")\n'
    if not write_file(wrapper, body) then return false end
    local ok = run("typst", { "compile", "--root", cache_dir(), wrapper, pdf })
    os.remove(wrapper)
    return ok
  end,
}

local warned_no_converter = false

local function svg_to_pdf(svg_path)
  local pdf_path = svg_path:gsub("%.svg$", "") .. ".pdf"
  if file_exists(pdf_path) then return pdf_path end
  for _, convert in ipairs(converters) do
    if convert(svg_path, pdf_path) and file_exists(pdf_path) then
      return pdf_path
    end
  end
  if not warned_no_converter then
    warned_no_converter = true
    io.stderr:write("[WARNING] inline_svg.lua: SVG を PDF に変換できませんでした。"
      .. "rsvg-convert / inkscape / typst のいずれかを PATH に入れてください。\n")
  end
  return nil
end

-- --- SVG ソース -> キャッシュ済みファイル ------------------------------------

local function normalize_svg(src)
  -- xmlns の無い SVG はレンダラが解釈できないことがあるので補う
  if not src:find("xmlns%s*=") then
    src = src:gsub("^(%s*<svg)", '%1 xmlns="http://www.w3.org/2000/svg"', 1)
  end
  return src
end

local function cache_svg(src)
  src = normalize_svg(src)
  local path = cache_dir() .. "/" .. utils.sha1(src) .. ".svg"
  if not file_exists(path) then write_file(path, src) end
  return path
end

-- --- raw HTML の <svg> 収集 --------------------------------------------------

local function inline_text(il)
  local t = il.t
  if t == "RawInline" and il.format == "html" then return il.text end
  if t == "Str" then return il.text end
  if t == "Space" then return " " end
  if t == "SoftBreak" or t == "LineBreak" then return "\n" end
  return nil
end

local function block_text(b)
  if b.t == "RawBlock" and b.format == "html" then return b.text end
  if b.t == "Plain" or b.t == "Para" then
    -- SVG の中身は RawInline (タグ) と Str (テキストノード) に分解される
    local parts = {}
    for _, il in ipairs(b.content) do
      local s = inline_text(il)
      if not s then return nil end
      parts[#parts + 1] = s
    end
    return table.concat(parts)
  end
  return nil
end

local function opens_svg(text)
  return text ~= nil and text:match("^%s*<svg[%s>]") ~= nil
end

local function closes_svg(text)
  return text:find("</svg%s*>") ~= nil
end

local function gather_blocks(blocks)
  local out = pandoc.Blocks({})
  local changed = false
  local i = 1
  while i <= #blocks do
    local consumed = 0
    local text = block_text(blocks[i])
    if opens_svg(text) then
      local parts, j, closed = {}, i, false
      while j <= #blocks do
        local t = (j == i) and text or block_text(blocks[j])
        if t == nil then break end
        parts[#parts + 1] = t
        if closes_svg(t) then closed = true break end
        j = j + 1
      end
      -- 閉じタグが見つからないときは触らない (後続の段落まで飲み込まないため)
      if closed then
        local path = cache_svg(table.concat(parts, "\n"))
        out:insert(pandoc.Para({ pandoc.Image({}, path) }))
        changed = true
        consumed = j - i + 1
      end
    end
    if consumed == 0 then
      out:insert(blocks[i])
      consumed = 1
    end
    i = i + consumed
  end
  if changed then return out end
end

local function gather_inlines(inlines)
  local out = pandoc.Inlines({})
  local changed = false
  local i = 1
  while i <= #inlines do
    local consumed = 0
    local il = inlines[i]
    if il.t == "RawInline" and il.format == "html" and opens_svg(il.text) then
      local parts, j, closed = {}, i, false
      while j <= #inlines do
        local t = inline_text(inlines[j])
        if t == nil then break end
        parts[#parts + 1] = t
        if closes_svg(t) then closed = true break end
        j = j + 1
      end
      if closed then
        local path = cache_svg(table.concat(parts))
        out:insert(pandoc.Image({}, path))
        changed = true
        consumed = j - i + 1
      end
    end
    if consumed == 0 then
      out:insert(inlines[i])
      consumed = 1
    end
    i = i + consumed
  end
  if changed then return out end
end

-- --- Image (.svg) を engine 別に差し替え --------------------------------------

-- pandoc の寸法指定 (50%, 8cm, 120px ...) を typst の長さへ写す
local function typst_length(dim)
  if not dim or dim == "" then return nil end
  local n, unit = dim:match("^%s*([%d%.]+)%s*(%a*%%?)%s*$")
  if not n then return nil end
  if unit == "%" then return n .. "%" end
  if unit == "" then unit = "px" end
  if unit == "px" then
    -- CSS px は 1/96in、typst の pt は 1/72in
    return string.format("%.4gpt", tonumber(n) * 72 / 96)
  end
  if unit == "cm" or unit == "mm" or unit == "in" or unit == "pt" or unit == "em" then
    return n .. unit
  end
  return nil
end

-- typst の文字列リテラルへ埋め込める形に逃がす
local function typst_string(s)
  s = s:gsub("\\", "\\\\")
  s = s:gsub('"', '\\"')
  s = s:gsub("\r", "\\r")
  s = s:gsub("\n", "\\n")
  return s
end

local warned_missing = {}

local function handle_image(img)
  if not img.src:lower():match("%.svg$") then return nil end
  local path = absolute(img.src)
  if not file_exists(path) then
    if not warned_missing[path] then
      warned_missing[path] = true
      io.stderr:write("[WARNING] inline_svg.lua: SVG が見つかりません: " .. img.src .. "\n")
    end
    return nil
  end

  if IS_TYPST then
    local data = read_file(path)
    if not data then return nil end
    local opts = {}
    local w = typst_length(img.attributes["width"])
    local h = typst_length(img.attributes["height"])
    if w then opts[#opts + 1] = "width: " .. w end
    if h then opts[#opts + 1] = "height: " .. h end
    -- Image のまま渡すと pandoc が rsvg-convert を探しに行くので raw で埋める。
    -- パス参照だと typst の sandbox (root 外を読めない) に阻まれるため、
    -- SVG ソースを bytes() として .typ に直接埋め込む。
    local args = 'bytes("' .. typst_string(data) .. '"), format: "svg"'
    if #opts > 0 then args = args .. ", " .. table.concat(opts, ", ") end
    -- box で包まないと typst が画像をブロック要素として扱い、文中に置いたとき
    -- 前後で改行が入る (pandoc 自身も通常の画像を #box(image(...)) で出す)
    return pandoc.RawInline("typst", "#box(image(" .. args .. "))")
  end

  -- LaTeX: \includegraphics が読める PDF に変換して差し替える。
  -- 変換結果はキャッシュ側に置き、参照元 SVG の隣は汚さない。
  local data = read_file(path)
  if not data then return nil end
  local pdf = svg_to_pdf(cache_svg(data))
  if not pdf then return nil end
  img.src = pdf
  return img
end

if not (IS_TYPST or IS_LATEX) then return {} end

return {
  { Blocks = gather_blocks },
  { Inlines = gather_inlines },
  { Image = handle_image },
}
