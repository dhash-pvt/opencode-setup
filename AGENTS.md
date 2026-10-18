# Rules for this repo

## Before editing
1. Read the target file first. If the task touches other files, call
   `codekit_find_local_import_dependencies` and read the files it lists.
2. Before moving or renaming a function, call `codekit_find_reference_files`
   and read every file it returns.

## Editing
- Changing one function: use `codekit_write_function_implementation`
  (body only, no `def` line). Never rewrite a whole file for this.
- Moving a function: `codekit_extract_function_definition` -> add it to the
  destination -> `codekit_remove_function_definition` -> fix every import
  found in the earlier step.
- Keep signatures, docstrings, imports and unrelated code exactly as they are.

## Boundaries
- Only touch files the task names, or files that need an import fix.
- Do not create files (tests, scratch, notes) unless asked.
- Do not install packages or run git commands that change state.
- Run tests at most once after a change. If they pass, stop.
  Never repeat a command that already failed the same way.
- If a tool is denied, stop and tell me. Do not look for a workaround.

## Finish
End with: files changed, and the commands you ran.