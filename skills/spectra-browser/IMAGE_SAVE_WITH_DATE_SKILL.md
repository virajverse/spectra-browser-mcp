---
name: spectra-browser-image-save-with-date
description: >-
  Browser image extraction saver for SpectraBrowser MCP. Extracts full-resolution
  originals via browser_extract_images then saves into date-wise folders under
  "Download Image with date/YYYY-MM-DD/<descriptive-name>_HHMMSS.ext". Never uses
  generic names like gpt.png. Use for any ChatGPT / web image download task.
---

# Image Save With Date — Spectra Browser Skill

Base folder (fixed, do not change without user approval):

```
D:\Company work\research\spectra-browser-mcp-main\Download Image with date
```

Final layout:

```
Download Image with date/
  2026-10-09/
    diwali-sale-poster_143210.png
    diwali-sale-poster_143255.webp
  2026-10-10/
    yoga-banner-hindi_101512.jpg
```

## 1. Mandatory rules

1. **Date-wise folder is compulsory.** Format `YYYY-MM-DD`. Never save loose files in base root.
2. **Descriptive name compulsory.** 3-5 words, lowercase, hyphens only. NEVER `gpt.png`, `image.png`, `chatgpt.png`, `download.png` alone.
   - Bad: `gpt`, `image`, `img`
   - Good: `diwali-sale-poster`, `yoga-banner-hindi`, `erp-dashboard-dark`
3. If user gives no name, ASK once via `session_ask_human`, or derive from prompt (first 4-5 meaningful words). Never invent misleading names.
4. **Original quality first.** Always `browser_extract_images`, never viewport screenshot crop.
5. One image = one timestamped file: `<name>_HHMMSS.<ext>`. Collision → append `_1`, `_2`.

## 2. Workflow (copy-paste order)

```
1. POST /extension_status {}
   -> extension_connected must be true, else give Setup Hub link, STOP.

2. POST /browser_tabs {}
   POST /browser_select_tab {"tab_id":"<string-id>","session_id":"default"}

3. POST /page_inspect {"session_id":"default"}
   -> fresh observation_id lo (stale ref fail hota hai).

4. ChatGPT generate ke baad:
   POST /browser_wait_idle {"timeout_ms":8000,"session_id":"default"}
   POST /browser_wait {"ms":2500,"session_id":"default"}

5. Dated folder banao + extract (save_dir me dated path do):
   POST /browser_extract_images {
     "session_id": "default",
     "save_dir": "D:/Company work/research/spectra-browser-mcp-main/Download Image with date/2026-10-09"
   }
   -> returns {save_directory, images:[{file_path, width, height, size_kb, format}]}

6. Rename with helper (confusion-free naming):
   python "D:/Company work/research/spectra-browser-mcp-main/skills/spectra-browser/save_image_with_date.py" --batch "<save_directory>" --name "<descriptive-name>"
   # single file: python .../save_image_with_date.py "<file_path>" --name "<descriptive-name>"

7. Verify: folder list karo, count + final path user ko do.
```

## 3. NEW image generate karna (ChatGPT composer note)

`browser_type` ChatGPT ke ProseMirror editor par hang hota hai (120s timeout) — uski jagah ye flow use karo:

```
1. POST /browser_navigate {"url":"https://chatgpt.com/?q=<url-encoded-prompt>"}
   -> prompt box me pre-fill ho jata hai (screenshot se verify karo)

2. Editor me pakka text bharo (execCommand = React-compatible input events):
   POST /script_library_add {"name":"fill-send","js_code":"(()=>{const ed=document.querySelector('#prompt-textarea'); if(!ed) return 'NO_EDITOR'; ed.focus(); document.execCommand('selectAll',false,null); document.execCommand('insertText',false,'<PROMPT>'); const btn=document.querySelector('button[data-testid=\"send-button\"]'); const txt=(ed.textContent||'').slice(0,50); if(btn){btn.click(); return 'FILLED_AND_CLICKED:'+txt;} return 'FILLED_NO_BTN:'+txt;})()"}
   POST /script_library_run {"name":"fill-send"}
   -> 'FILLED_AND_CLICKED:...' aana chahiye. 'FILLED_NO_BTN' aaye to find-send script se dobara button dhoondho, phir send-button click script chalao.

3. 60-90s wait (image gen slow hai), phir page_inspect me
   role=img + estuary/generated naam check karo. Tabhi extract karo.
```

Gotcha: synthetic KeyboardEvent Enter React ignore karta hai; coordinate click viewport scaling se miss ho sakta hai. execCommand + send-button click hi reliable hai.

## 4. Verified payloads

```json
POST /browser_extract_images {"session_id":"default","save_dir":"D:/Company work/research/spectra-browser-mcp-main/Download Image with date/2026-10-09"}
// -> {status:"success", total_extracted:2, save_directory:".../2026-10-09", images:[{file_path, format, size_kb}]}
```

Helper:

```bash
python "D:/Company work/research/spectra-browser-mcp-main/skills/spectra-browser/save_image_with_date.py" "D:/.../extracted_images/image_123_1.png" --name "diwali-sale-poster"
# -> D:/Company work/research/spectra-browser-mcp-main/Download Image with date/2026-10-09/diwali-sale-poster_143210.png
```

## 5. YE MAT KARO — Strict Don'ts (problem se bachne ke liye)

Prompt / typing:
- ❌ `browser_type` ChatGPT composer me MAT chalao — 120s hang hota hai, session block ho jata hai. Section 3 wala JS flow use karo.
- ❌ Synthetic `KeyboardEvent Enter` dispatch MAT karo submit ke liye — React ignore karta hai, prompt box me pada rehta hai.
- ❌ Send button par andaza coordinate click MAT karo pehli koshish me — viewport scaling se miss hota hai. Pehle a11y ref, nahi mile to `find-send` script se selector confirm karke JS click karo.
- ❌ Submit ke turant baad extract MAT karo — generation 60-120s leti hai. Pehle `page_inspect` me `role=img` + `estuary/generated` dikhe, TABHI extract karo. `total_extracted:0` ka matlab image abhi bani nahi (ya dedup), error nahi.

Naming / folders:
- ❌ Generic naam KABHI nahi: `gpt`, `chatgpt`, `image`, `img`, `download`, `screenshot`, `untitled` — helper reject karega, dobara mehnat hogi.
- ❌ Base root (`Download Image with date/` ke andar seedha) me file MAT rakho — hamesha `YYYY-MM-DD/` subfolder me.
- ❌ Base folder path user approval ke bina MAT badlo.
- ❌ Original extension MAT badlo (`.png` → `.jpg` manual rename nahi) — format wahi jo extract ne diya.

Quality:
- ❌ Viewport screenshot crop ko "original image" bolkar MAT do — hamesha `browser_extract_images` (full-res CDN blob). Screenshot sirf last fallback hai.
- ❌ Extract se pehle page se navigate/reload MAT karo — generation marr jayegi aur refs expire ho jayenge.

Safety (destructive / session):
- ❌ `/tab_close` MAT chalao — user ka asli Chrome tab band ho jayega (ye naya tab nahi kholta).
- ❌ `/session_close` MAT chalao beech task me — session marr jayegi.
- ❌ `browser_register_start/confirm/revoke` live registration par MAT chalao — connected profile bigad jayegi.
- ❌ `clean_mcp_storage` bina `dry_run:true` pehle dekhe MAT chalao.
- ❌ Stale `observation_id` reuse MAT karo — har click/type se pehle fresh `page_inspect` lo.
- ❌ `tab_id` int me MAT bhejo — hamesha string (`"148783960"`), nahi to 422 error.
- ❌ User ke saamne login/password ya token output me MAT dikhao/log karo.

## 6. Gotchas

- `save_dir` absolute path do, relative nahi. Forward-slash (`D:/...`) safest hai.
- `browser_extract_images` SHA-256 dedup karta hai — same image dobara 0 count dega, ye normal hai.
- Screenshot fallback sirf tab jab extract 0 de: `browser_screenshot(save_to_disk=true)` phir helper se dated folder me move karo.
- Base root me file mili to helper se turant dated folder me shift karo, root hamesha khaali rakho.
