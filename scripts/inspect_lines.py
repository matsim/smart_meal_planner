import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'frontend/src/pages/RecipeEditor.tsx'
lines = open(path, encoding='utf-8').readlines()

# Check what is on lines 409-418 (0-indexed: 408-417)
for i, l in enumerate(lines[406:420], start=407):
    print(i, repr(l[:80]))
