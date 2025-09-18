#!/usr/bin/env python3
import sys

print(f"引数の数: {len(sys.argv) - 1}")
print(f"すべての引数: {' '.join(sys.argv[1:])}")
print("引数を個別に表示:")
for i, arg in enumerate(sys.argv[1:], 1):
    print(f"  引数{i}: {arg}")