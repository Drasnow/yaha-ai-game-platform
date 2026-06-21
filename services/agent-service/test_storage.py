import re

# 正确方案: \s* 放在 lookahead 之后，让 lookahead 在 \s* 消耗空格之前检查
# Pattern A: Storage[key]  - 拦截 [ 后紧跟的不是引号
pA = re.compile(r"\b(?:local|session)Storage\s*\[(?!\s*['\"])", re.IGNORECASE)
# Pattern B: Storage.method(.) - 拦截 .method( 后第一个字符不是引号（. 不在 [\w] 内，算独立 token）
# 核心: (?:(?!\s*['\"])[^()])* 只在遇到 ( 或 引号 时停止，) 会让它停止
pB = re.compile(
    r"\b(?:local|session)Storage"
    r"\.(?:getItem|setItem|removeItem)"
    r"\((?:(?!\s*['\"])[^()])*",
    re.IGNORECASE,
)

cases = [
    # 安全: 静态字符串 key
    ("localStorage.setItem('score', v)", True),
    ("localStorage.getItem('best')", True),
    ("localStorage['score']", True),
    ('localStorage["best"]', True),
    ("localStorage.removeItem('x')", True),
    ("localStorage.clear()", True),
    ("localStorage[  'score'  ]", True),  # 空格后接引号，安全
    # 危险: 变量 key
    ("localStorage[keyVar]", False),
    ("localStorage[userInput]", False),
    ("localStorage.getItem(key)", False),
    ("localStorage.setItem(keyVar, v)", False),
    ("localStorage[ 'dynamic' + x ]", False),  # [ 后先空格再引号，但 + 不是引号
]

def check(code):
    return (pA.search(code) is None) and (pB.search(code) is None)

print(f"Pattern A: {pA.pattern}")
print(f"Pattern B: {pB.pattern}")
print("=" * 70)
all_ok = True
for code, expect_safe in cases:
    is_safe = check(code)
    ok = is_safe == expect_safe
    all_ok = all_ok and ok
    status = "PASS" if is_safe else "BLOCK"
    mark = "OK" if ok else "FAIL"
    print(f"[{mark}] [{status:5}] {repr(code)}")

print("=" * 70)
print(f"Result: {'ALL PASSED ✓' if all_ok else 'SOME FAILED'}")
