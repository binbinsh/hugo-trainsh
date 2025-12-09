# hugo-trainsh

## General Instructions
- Always `use context7` for the most recent docs and best practices.
- All comments and documentations in English.
- Include only brief end-user instructions in the root README.md file.
- Place concise README.md alongside related source code (include TOC if detailed).
- Always prioritize ast-grep (cmd: `sg`) over regex/string-replace for code manipulation, using AST patterns to ensure structural accuracy and avoid syntax errors. Examples:
    1. Swap Args: `sg run -p 'fn($A, $B)' -r 'fn($B, $A)'`
    2. Wrap Error: `sg run -p 'return $E' -r 'return wrap($E)'`
    3. API Update: `sg run -p 'user.id' -r 'user.get_id()'`

## Styling Instruction
- Only use Tailwind CSS v4 for styling only
- Use Tailwind CSS v4 in Hugo: https://gohugo.io/functions/css/tailwindcss/

