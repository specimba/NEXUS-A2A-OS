import sys

filepath = 'nexus_os/security/meta_attack_detector.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

bs = chr(92)
# File currently has raw string with FOUR backslashes: r"(?:\\\\u...)
# We need raw string with TWO backslashes: r"(?:\\u...)
broken = '        (r"(?:' + bs*4 + 'u[0-9a-fA-F]{4,8}){4,}", 0.90),'
fixed = '        (r"(?:' + bs*2 + 'u[0-9a-fA-F]{4,8}){4,}", 0.90),'

print('broken repr:', repr(broken))
print('fixed repr:', repr(fixed))
print('broken in content:', broken in content)

if broken in content:
    content = content.replace(broken, fixed)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed nexus_os/security/meta_attack_detector.py')
else:
    print('broken pattern not found in nexus_os file')

# Also fix src version if needed
src_filepath = 'src/nexus_os/security/meta_attack_detector.py'
with open(src_filepath, 'r', encoding='utf-8') as f:
    src_content = f.read()

if broken in src_content:
    src_content = src_content.replace(broken, fixed)
    with open(src_filepath, 'w', encoding='utf-8') as f:
        f.write(src_content)
    print('Fixed src/nexus_os/security/meta_attack_detector.py')
else:
    print('broken pattern not found in src file')
