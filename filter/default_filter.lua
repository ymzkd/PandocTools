function Math(el)
  -- DisplayMathのみを処理
  if el.mathtype == "DisplayMath" then
    local text = el.text or ""
    
    -- 数式環境をチェック（より単純なパターン）
    local has_env = text:find("\\begin{align") or 
                   text:find("\\begin{gather") or
                   text:find("\\begin{multline") or
                   text:find("\\begin{equation") or
                   text:find("\\begin{flalign") or
                   text:find("\\begin{alignat")
    
    if has_env then
      -- io.stderr:write("Math environment detected\n")
      -- 単純にテキストを返す
      return pandoc.RawInline("latex", text)
    end
  end
end
