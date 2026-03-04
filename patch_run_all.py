import re

with open('run_all_strategies.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace references to check-new-indicators
content = content.replace('check-new-indicators', 'check-indicator-combo')
content = content.replace('skip_new_indicators', 'skip_indicator_combo')
content = content.replace('--skip-new-indicators', '--skip-indicator-combo')
content = content.replace('新指标分析', '指标组合分析')
content = content.replace('新指标', '指标组合')

# Add check-volume-confirmation (Phase 6) to build_steps
import_volume_step = """
    # 4.5 量价确认分析
    if not skip_volume_confirmation:
        cmd = [sys.executable, "main.py", *end_date_args]
        if limit:
            cmd.extend(["--limit", str(limit)])
        if browser_silent:
            cmd.append("--no-open")
        steps.append(
            Step(
                name="量价确认分析 (check-volume-confirmation)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-volume-confirmation",
                group="analysis",
            )
        )
"""

# We need to inject `--limit` handling
content = content.replace('end_date: Optional[str],', 'end_date: Optional[str],\n    limit: Optional[int],')
content = content.replace('end_date=args.end_date,', 'end_date=args.end_date,\n        limit=args.limit,')
content = content.replace('skip_indicator_combo: bool,', 'skip_indicator_combo: bool,\n    skip_volume_confirmation: bool,')
content = content.replace('skip_indicator_combo=args.skip_indicator_combo,', 'skip_indicator_combo=args.skip_indicator_combo,\n        skip_volume_confirmation=args.skip_volume_confirmation,')

# Add limit arg to commands
content = content.replace('cmd.extend(end_date_args)', 'cmd.extend(end_date_args)\n        if limit:\n            cmd.extend(["--limit", str(limit)])')

# Insert volume confirmation step before generating reports index
content = content.replace('    # 5. 生成报告索引', import_volume_step + '\n    # 5. 生成报告索引')

with open('run_all_strategies.py', 'w', encoding='utf-8') as f:
    f.write(content)

