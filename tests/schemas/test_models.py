from app.schemas import DBContext, SQLOutput


def test_db_context_dataclass():
    ctx = DBContext(connection="conn", schema_info={})
    assert ctx.connection == "conn"
    assert ctx.schema_info == {}


def test_sql_output_defaults():
    out = SQLOutput(sql_query="SELECT 1")
    assert out.sql_query == "SELECT 1"
    assert out.explanation is None
    assert 0.0 <= out.confidence <= 1.0

