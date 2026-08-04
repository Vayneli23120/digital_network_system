"""
Streaming 层测试（批次八切片 B）：/ws/deploy/{session_id} WebSocket 错误路径。

只覆盖畸形请求触发 ValidationError 的分支（websocket/router.py:276-287）：
发缺 target_devices 的请求 → 先发 deploy_error 再发 deploy_complete(success=False)。
该分支在任一 DB/auth 依赖之前 return，因此无需真实凭证/数据库。

成功路径（需 authorize_deploy_token + 凭证解密）成本高，由
test_deploy_stream_service.py 的直测覆盖业务流。
"""


class TestDeployWsEndpoint:
    def test_malformed_request_emits_error_then_complete(self, router_client_factory):
        from app.features.websocket import router as websocket_router

        client = router_client_factory(websocket_router.router)

        with client.websocket_connect("/ws/deploy/sess-bad-1") as ws:
            # 缺必填 target_devices → model_validate 抛 ValidationError
            ws.send_json({"action": "start_deploy"})

            err = ws.receive_json()
            assert err["type"] == "deploy_error"
            assert "无效" in err["message"]

            complete = ws.receive_json()
            assert complete["type"] == "deploy_complete"
            assert complete["success"] is False
