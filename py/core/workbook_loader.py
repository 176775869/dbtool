"""workbook_loader.py —— 查找备份 Excel 文件，返回文件路径"""
import os, glob

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backup')

def get_workbook_path(year=None):
    """返回指定年份的 Excel 文件路径，未指定则取最新文件"""
    if year is None:
        from datetime import datetime
        year = datetime.now().strftime('%Y')
    pattern = os.path.join(BACKUP_DIR, f'交易复盘记录{year}.xlsx')
    files = glob.glob(pattern)
    if files:
        return files[0]
    # 回退到最新文件
    all_files = glob.glob(os.path.join(BACKUP_DIR, '交易复盘记录*.xlsx'))
    if all_files:
        return max(all_files, key=os.path.getmtime)
    return None
