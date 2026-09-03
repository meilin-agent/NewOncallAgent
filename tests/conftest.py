# pytest 共享配置
# 把项目根目录加入 sys.path,使测试能直接导入 internal/utility/api 包。

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
