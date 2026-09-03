# MySQL 数据库操作工具(对应 Go 版 internal/ai/tools/mysql_crud.go)
# 差异说明:Go 版在执行前有 stdin 交互确认("请确定是否执行本sql(y/n)"),
# 在 HTTP 服务进程里该确认会阻塞线程且无输入源,Python 版按方案移除确认直接执行。

import json

TOOL_NAME = "mysql_crud"

TOOL_DESCRIPTION = (
    "Execute SQL queries against the MySQL database and return results in JSON format. Use this "
    "tool when you need to query, insert, update or delete data from the database. The results "
    "will be formatted as JSON for easy parsing."
)

SPEC = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "dsn": {
                    "type": "string",
                    "description": "The Data Source Name for connecting to the MySQL database, "
                    "including username, password, host, port, and database name",
                },
                "sql": {
                    "type": "string",
                    "description": "The SQL query to execute against the MySQL database",
                },
                "operate_type": {
                    "type": "string",
                    "description": "The type of SQL operation to perform: query, insert, update, "
                    "or delete",
                },
            },
            "required": ["dsn", "sql", "operate_type"],
        },
    },
}


def _parse_dsn(dsn: str) -> dict:
    """解析 Go GORM 风格的 DSN:user:password@tcp(host:port)/dbname?params"""
    import re

    m = re.match(r"^([^:]+):(.*)@tcp\(([^:]+):(\d+)\)/([^?]+)", dsn)
    if not m:
        raise ValueError(f"无法解析 DSN(期望格式 user:password@tcp(host:port)/dbname):{dsn}")
    user, password, host, port, dbname = m.groups()
    return {"host": host, "port": int(port), "user": user, "password": password, "database": dbname}


def mysql_crud(args: dict) -> str:
    """执行 SQL;query 类型返回行数据 JSON,其余返回执行结果。PyMySQL 惰性导入。"""
    import pymysql

    dsn = args.get("dsn", "")
    sql = args.get("sql", "")
    operate_type = (args.get("operate_type") or "").lower()

    conn_kwargs = _parse_dsn(dsn)
    conn_kwargs["charset"] = "utf8mb4"
    conn = pymysql.connect(**conn_kwargs)
    try:
        with conn.cursor() as cursor:
            if operate_type == "query":
                cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [d[0] for d in cursor.description] if cursor.description else []
                result = [dict(zip(columns, row)) for row in rows]
                return json.dumps({"success": True, "rows": result}, ensure_ascii=False, default=str)
            affected = cursor.execute(sql)
            conn.commit()
            return json.dumps({"success": True, "affected": affected}, ensure_ascii=False)
    finally:
        conn.close()
