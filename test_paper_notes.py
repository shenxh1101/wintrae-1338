#!/usr/bin/env python3
"""
测试脚本 - 验证 paper-notes 工具功能
"""

import os
import sys
import tempfile
import shutil
import subprocess
import json


def run_command(cmd, cwd=None):
    print(f"\n$ {cmd}")
    print("-" * 60)
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    print("-" * 60)
    return result.returncode


def main():
    test_dir = tempfile.mkdtemp(prefix='paper_notes_test_')
    print(f"测试目录: {test_dir}")

    try:
        paper_notes_cmd = f'python -m paper_notes.cli'

        print("\n" + "=" * 60)
        print("测试 1: 初始化文献库")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} init {test_dir}')
        assert rc == 0, "init 命令失败"

        print("\n" + "=" * 60)
        print("测试 2: 检查目录结构")
        print("=" * 60)
        for root, dirs, files in os.walk(test_dir):
            level = root.replace(test_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f'{indent}{os.path.basename(root)}/')
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f'{subindent}{file}')

        os.makedirs(os.path.join(test_dir, 'test_data'), exist_ok=True)
        pdf_path = os.path.join(test_dir, 'test_data', 'test_paper.pdf')
        with open(pdf_path, 'w') as f:
            f.write('%PDF-1.4 test')

        summary_path = os.path.join(test_dir, 'test_data', 'summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("""# Test Paper on Deep Learning

作者: John Doe, Jane Smith
年份: 2023
会议/期刊: ICML

## 摘要
这是一篇关于深度学习的测试论文摘要。

## 引用摘录
- "Deep learning is a subset of machine learning."
- "Neural networks can learn complex patterns."

## 待解决问题
- 如何提高模型的泛化能力？
- 过拟合问题如何解决？

## 笔记
- 这是一篇测试论文
- 需要后续精读
""")

        print("\n" + "=" * 60)
        print("测试 3: 导入单篇论文（带摘要）")
        print("=" * 60)
        rc = run_command(
            f'{paper_notes_cmd} import {pdf_path} -s {summary_path} --tags "深度学习" "测试" --author "John Doe" --year-tag 2023',
            cwd=test_dir
        )
        assert rc == 0, "import 命令失败"

        print("\n" + "=" * 60)
        print("测试 4: 导入更多测试文献")
        print("=" * 60)

        for i in range(1, 6):
            pdf_path_i = os.path.join(test_dir, 'test_data', f'paper_{i}.pdf')
            with open(pdf_path_i, 'w') as f:
                f.write('%PDF-1.4 test')

            title = f"Paper {i} on {'NLP' if i % 2 == 0 else 'CV'}"
            authors = f"Author {i}"
            year = 2020 + i
            rc = run_command(
                f'{paper_notes_cmd} import {pdf_path_i} -t "{title}" -a "{authors}" -y {year} --tags {"NLP" if i%2==0 else "CV"}',
                cwd=test_dir
            )
            assert rc == 0, f"导入第 {i} 篇文献失败"

        print("\n" + "=" * 60)
        print("测试 5: 列出所有标签")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} tag --list', cwd=test_dir)
        assert rc == 0, "tag list 命令失败"

        print("\n" + "=" * 60)
        print("测试 6: 为文献打标签")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} tag --ids 2,3,4 --add "重要"', cwd=test_dir)
        assert rc == 0, "tag add 命令失败"

        print("\n" + "=" * 60)
        print("测试 7: 标记阅读状态")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} tag --ids 1 --read', cwd=test_dir)
        assert rc == 0, "标记已读失败"

        rc = run_command(f'{paper_notes_cmd} tag --ids 2,3 --reading', cwd=test_dir)
        assert rc == 0, "标记在读失败"

        rc = run_command(f'{paper_notes_cmd} tag --ids 4,5 --to-review', cwd=test_dir)
        assert rc == 0, "标记待精读失败"

        print("\n" + "=" * 60)
        print("测试 8: 设置阅读进度")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} tag --ids 2 --progress 50', cwd=test_dir)
        assert rc == 0, "设置进度失败"

        print("\n" + "=" * 60)
        print("测试 9: 搜索文献 - 关键词")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} search "Deep" --show-tags', cwd=test_dir)
        assert rc == 0, "关键词搜索失败"

        print("\n" + "=" * 60)
        print("测试 10: 搜索文献 - 标签组合")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} search --tags "深度学习" "重要"', cwd=test_dir)
        assert rc == 0, "标签组合搜索失败"

        print("\n" + "=" * 60)
        print("测试 11: 搜索文献 - 状态筛选")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} search --status reading', cwd=test_dir)
        assert rc == 0, "状态筛选搜索失败"

        print("\n" + "=" * 60)
        print("测试 12: 查看文献详情")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} search --detail 1', cwd=test_dir)
        assert rc == 0, "查看详情失败"

        print("\n" + "=" * 60)
        print("测试 13: 导出阅读清单")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} export list -o {test_dir}/export/reading_list.md', cwd=test_dir)
        assert rc == 0, "导出阅读清单失败"

        print("\n" + "=" * 60)
        print("测试 14: 导出引用摘录")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} export quotes -o {test_dir}/export/quotes.md', cwd=test_dir)
        assert rc == 0, "导出引用摘录失败"

        print("\n" + "=" * 60)
        print("测试 15: 导出待办问题")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} export questions -o {test_dir}/export/questions.md', cwd=test_dir)
        assert rc == 0, "导出待办问题失败"

        print("\n" + "=" * 60)
        print("测试 16: 导出全部")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} export all -o {test_dir}/export/all', cwd=test_dir)
        assert rc == 0, "导出全部失败"

        print("\n" + "=" * 60)
        print("测试 17: 检查导出文件")
        print("=" * 60)
        export_dir = os.path.join(test_dir, 'export')
        if os.path.exists(export_dir):
            for f in os.listdir(export_dir):
                fpath = os.path.join(export_dir, f)
                size = os.path.getsize(fpath)
                print(f"  {f} ({size} bytes)")

        print("\n" + "=" * 60)
        print("测试 18: 统计总览")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} stats', cwd=test_dir)
        assert rc == 0, "统计总览失败"

        print("\n" + "=" * 60)
        print("测试 19: 月度统计")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} stats --monthly', cwd=test_dir)
        assert rc == 0, "月度统计失败"

        print("\n" + "=" * 60)
        print("测试 20: 主题分布")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} stats --topics --drilldown', cwd=test_dir)
        assert rc == 0, "主题分布失败"

        print("\n" + "=" * 60)
        print("测试 21: 状态分布")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} stats --status', cwd=test_dir)
        assert rc == 0, "状态分布失败"

        print("\n" + "=" * 60)
        print("测试 22: 长期未处理文献")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} stats --stale --stale-days 0', cwd=test_dir)
        assert rc == 0, "长期未处理文献失败"

        print("\n" + "=" * 60)
        print("测试 23: 批量修改分类")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} tag --recategorize 重要 topic', cwd=test_dir)
        assert rc == 0, "修改分类失败"

        print("\n" + "=" * 60)
        print("测试 24: 移除标签")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} tag --ids 2 --remove 测试', cwd=test_dir)
        assert rc == 0, "移除标签失败"

        print("\n" + "=" * 60)
        print("测试 25: 帮助信息")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} --help', cwd=test_dir)
        assert rc == 0, "帮助信息失败"

        rc = run_command(f'{paper_notes_cmd} import --help', cwd=test_dir)
        assert rc == 0, "import 帮助失败"

        print("\n" + "=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)

        print("\n测试结果汇总:")
        print("  [OK] init 命令 - 初始化文献库")
        print("  [OK] import 命令 - 单个导入、批量导入")
        print("  [OK] tag 命令 - 打标签、改状态、改分类、移标签")
        print("  [OK] search 命令 - 关键词、标签、状态、详情")
        print("  [OK] export 命令 - 阅读清单、引用摘录、待办问题")
        print("  [OK] stats 命令 - 总览、月度、主题、状态、长期未处理")
        print(f"\n测试目录: {test_dir}")
        print("可以手动检查目录结构和导出文件")

        return 0

    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        pass


if __name__ == '__main__':
    sys.exit(main())
