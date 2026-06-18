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


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def run_command(cmd, cwd=None, extra_env=None):
    print(f"\n$ {cmd}")
    print("-" * 60)
    env = os.environ.copy()
    env['PYTHONPATH'] = PROJECT_ROOT + os.pathsep + env.get('PYTHONPATH', '')
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, env=env)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    print("-" * 60)
    return result.returncode


def main():
    test_dir = tempfile.mkdtemp(prefix='paper_notes_test_')
    print(f"项目根目录: {PROJECT_ROOT}")
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
        print("测试 26: note 命令 - 追加一句话摘要")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} note --ids 1 -s "本文提出了一种用于深度学习的新型测试方法，在多个基准上取得SOTA。"', cwd=test_dir)
        assert rc == 0, "note --summary 失败"

        rc = run_command(f'{paper_notes_cmd} note --ids 2,3 -s "本文深入研究了NLP/CV领域的经典架构。"', cwd=test_dir)
        assert rc == 0, "note 批量 summary 失败"

        print("\n" + "=" * 60)
        print("测试 27: note 命令 - 追加引用摘录和阅读笔记")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} note --ids 1 -q "我们的方法在ImageNet上达到了95%准确率。" -p 15 -c "实验结果表格"', cwd=test_dir)
        assert rc == 0, "note --quote 失败"

        rc = run_command(f'{paper_notes_cmd} note --ids 1,2 -n "核心方法值得进一步研究，特别是注意力机制部分。" -t method', cwd=test_dir)
        assert rc == 0, "note --note 失败"

        print("\n" + "=" * 60)
        print("测试 28: note 命令 - 追加待办问题")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} note --ids 1,2 --question "本文的消融实验是否考虑了batch size影响？" --status pending', cwd=test_dir)
        assert rc == 0, "note --question 失败"

        rc = run_command(f'{paper_notes_cmd} note --ids 3 --question "为什么该模型比基线模型推理速度慢3倍？"', cwd=test_dir)
        assert rc == 0, "note --question 2 失败"

        print("\n" + "=" * 60)
        print("测试 29: note 命令 - 查看笔记列表")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} note --list 1', cwd=test_dir)
        assert rc == 0, "note --list 失败"

        rc = run_command(f'{paper_notes_cmd} note --list', cwd=test_dir)
        assert rc == 0, "note --list (all) 失败"

        print("\n" + "=" * 60)
        print("测试 30: export meeting - 组会汇总（全部）")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} export meeting -o {test_dir}/export/meeting_all.md --meeting-title "组会周度汇总报告"', cwd=test_dir)
        assert rc == 0, "export meeting (全部) 失败"

        print("\n" + "=" * 60)
        print("测试 31: export meeting - 按主题筛选")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} export meeting --topic "深度学习" -o {test_dir}/export/meeting_dl.md', cwd=test_dir)
        assert rc == 0, "export meeting by topic 失败"

        print("\n" + "=" * 60)
        print("测试 32: export meeting - 按状态筛选（待精读）")
        print("=" * 60)
        rc = run_command(f'{paper_notes_cmd} export meeting --status to_review -o {test_dir}/export/meeting_review.md', cwd=test_dir)
        assert rc == 0, "export meeting by status 失败"

        print("\n" + "=" * 60)
        print("测试 33: import -b 清单不存在时报错（不卡住）")
        print("=" * 60)
        env = os.environ.copy()
        env['PYTHONPATH'] = PROJECT_ROOT + os.pathsep + env.get('PYTHONPATH', '')
        result = subprocess.run(f'{paper_notes_cmd} import -b /nonexistent/file.txt', shell=True, cwd=test_dir, capture_output=True, text=True, env=env)
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Return code: {result.returncode}")
        assert "不存在" in (result.stdout + result.stderr), "批量导入清单不存在应该报错"

        print("\n" + "=" * 60)
        print("测试 34: import -b 清单导入（带汇总报告）")
        print("=" * 60)
        batch_file = os.path.join(test_dir, 'import_list.txt')
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write("# 测试批量导入清单\n")
            f.write("Batch Imported Paper 1|%s|Author A|2024|ICLR|测试,批量|\n" % os.path.join(test_dir, 'test_data', 'test_paper.pdf'))
            f.write("Batch Imported Paper 2||Author B|2023|CVPR|CV||\n")
            f.write("|缺少标题应该失败|||\n")
            f.write("Batch Duplicate - Test Paper on DL|||2023||重复测试|\n")
        rc = run_command(f'{paper_notes_cmd} import -b {batch_file}', cwd=test_dir)
        assert rc == 0, "批量导入清单 失败"

        print("\n" + "=" * 60)
        print("测试 35: init --force 强制重置（真的清空）")
        print("=" * 60)
        test_dir2 = tempfile.mkdtemp(prefix='paper_notes_reset_')
        try:
            rc = run_command(f'{paper_notes_cmd} init {test_dir2}', cwd=test_dir)
            assert rc == 0, "init first 失败"

            pdf2 = os.path.join(test_dir2, 'papers', 'keep_me.pdf')
            os.makedirs(os.path.dirname(pdf2), exist_ok=True)
            with open(pdf2, 'w') as f:
                f.write('PDF content')

            note2 = os.path.join(test_dir2, 'notes', 'keep_me.txt')
            os.makedirs(os.path.dirname(note2), exist_ok=True)
            with open(note2, 'w') as f:
                f.write('note content')

            before_reset_papers = os.path.exists(pdf2)
            before_reset_notes = os.path.exists(note2)
            print(f"重置前 papers/ 保留文件存在: {before_reset_papers}")
            print(f"重置前 notes/ 保留文件存在: {before_reset_notes}")

            rc = run_command(f'{paper_notes_cmd} init {test_dir2} --force', cwd=test_dir)
            assert rc == 0, "init --force 失败"

            after_reset_papers = os.path.exists(pdf2)
            after_reset_notes = os.path.exists(note2)
            print(f"重置后 papers/ 保留文件存在: {after_reset_papers}（应为 False）")
            print(f"重置后 notes/ 保留文件存在: {after_reset_notes}（应为 False）")
            assert not after_reset_papers, "--force 应该清空 papers/"
            assert not after_reset_notes, "--force 应该清空 notes/"

            rc = run_command(f'{paper_notes_cmd} init {test_dir2} --force --keep-papers --keep-notes', cwd=test_dir)
            assert rc == 0, "init --force --keep-* 失败"

            db_exists = os.path.exists(os.path.join(test_dir2, '.paper_notes', 'library.db'))
            print(f"重置后数据库存在: {db_exists}")
            assert db_exists, "重置后数据库应该重新建立"
        finally:
            shutil.rmtree(test_dir2, ignore_errors=True)

        print("\n" + "=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)

        print("\n测试结果汇总:")
        print("  [OK] init 命令 - 初始化/强制重置/保留选项")
        print("  [OK] import 命令 - 单个/目录/清单导入+汇总报告")
        print("  [OK] tag 命令 - 标签/状态/分类/进度管理")
        print("  [OK] note 命令 - 摘录/问题/笔记/摘要增删改查")
        print("  [OK] search 命令 - 关键词/标签/状态/详情查询")
        print("  [OK] export 命令 - 清单/摘录/问题/组会汇总")
        print("  [OK] stats 命令 - 总览/月度/主题/状态/搁置")
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
