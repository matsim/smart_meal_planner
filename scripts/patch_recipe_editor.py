import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'frontend/src/pages/RecipeEditor.tsx'
lines = open(path, encoding='utf-8').readlines()

# replace lines 409-418 (0-indexed: 408-417)
indent = '                                        '
replacement = [
    indent + '<input\n',
    indent + '    className="input-field"\n',
    indent + '    style={{ width: "160px", padding: "0.4rem", fontSize: "0.85rem" }}\n',
    indent + '    value={localSearch[idx] || ""}\n',
    indent + '    onChange={e => handleLocalSearchChange(idx, e.target.value)}\n',
    indent + '    placeholder="Lier (3 chars min...)"\n',
    indent + '/>\n',
]

new_lines = lines[:408] + replacement + lines[418:]
open(path, 'w', encoding='utf-8').writelines(new_lines)
print(f'Done. Old: {len(lines)}, New: {len(new_lines)} lines')
# verify
for i, l in enumerate(new_lines[406:418], start=407):
    print(i, repr(l[:80]))
