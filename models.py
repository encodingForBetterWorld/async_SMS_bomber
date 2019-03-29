from easy_tormysql import init_mysql, BaseModel, Field
init_mysql(default={
    "max_connections": 20,
    "idle_seconds": 7200,
    "wait_connection_timeout": 3,
    "host": "127.0.0.1",
    "user": "root",
    "passwd": "root",
    "charset": "utf8",
    "db": "test"
})


class Cloopen_sms(BaseModel):
    token = Field()
    sid = Field()
    app_id = Field()
    template_ids = Field()
    is_actived = Field(default=0)
