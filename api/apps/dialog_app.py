#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from flask import request
from flask_login import login_required, current_user
from api.db.services.dialog_service import DialogService
from api.db import StatusEnum
from api.db.services.llm_service import TenantLLMService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_service import TenantService, UserTenantService
from api import settings
from api.utils.api_utils import server_error_response, get_data_error_result, validate_request
from api.utils import get_uuid
from api.utils.api_utils import get_json_result
import logging

logging.basicConfig(level=logging.INFO)

@manager.route('/set', methods=['POST'])  # noqa: F821
@login_required
def set_dialog():
    req = request.json
    logging.info("req:%s",req)
    dialog_id = req.get("dialog_id")
    name = req.get("name", "New Dialog")
    description = req.get("description", "A helpful dialog")
    icon = req.get("icon", "")
    top_n = req.get("top_n", 6)
    top_k = req.get("top_k", 1024)
    rerank_id = req.get("rerank_id", "")
    if not rerank_id:
        req["rerank_id"] = ""
    similarity_threshold = req.get("similarity_threshold", 0.1)
    vector_similarity_weight = req.get("vector_similarity_weight", 0.3)
    llm_setting = req.get("llm_setting", {})
    default_prompt = {
        "system": """你是一个智能助手，请总结知识库的内容来回答问题，请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案！”这句话。回答需要考虑聊天历史。
以下是知识库：
{knowledge}
以上是知识库。""",
        "prologue": "您好，我是您的助手小樱，长得可爱又善良，can I help you?",
        "parameters": [
            {"key": "knowledge", "optional": False}

        ],
        'quote': True, 'keyword': False, 'tts': False,
        'llm_id':'deepseek-r1:32b@Ollama',
        'llm_setting':{'temperature': 0.1, 'top_p': 0.3, 'presence_penalty': 0.4, 'frequency_penalty': 0.7, 'max_tokens': 512},
        'similarity_threshold': 0.2, 
        'vector_similarity_weight': 0.30000000000000004, 
        'top_n': 8,
        "empty_response": "Sorry! 知识库中未找到相关内容！"
    }
    prompt_config = req.get("prompt_config", default_prompt)
    logging.info("prompt_config: %s",prompt_config)
    if "parameters" not in prompt_config or not prompt_config["parameters"]:
        prompt_config["parameters"] = default_prompt["parameters"]

    if "prologue" not in prompt_config or not prompt_config["prologue"]:
        prompt_config["prologue"] = default_prompt["prologue"]

    if "quote" not in prompt_config or not prompt_config["quote"]:
        prompt_config["quote"] = default_prompt["quote"]
    if "keyword" not in prompt_config or not prompt_config["keyword"]:
        prompt_config["keyword"] = default_prompt["keyword"]
    if "tts" not in prompt_config or not prompt_config["tts"]:
        prompt_config["tts"] = default_prompt["tts"]

    if "system" not in prompt_config or not prompt_config["system"]:
        prompt_config["system"] = default_prompt["system"]

    if 'vector_similarity_weight' not in prompt_config or not prompt_config["vector_similarity_weight"]:
        prompt_config["vector_similarity_weight"] = default_prompt["vector_similarity_weight"]

    if 'llm_setting' not in prompt_config or not prompt_config["llm_setting"]:
        prompt_config["llm_setting"] = default_prompt["llm_setting"]

    if 'similarity_threshold' not in prompt_config or not prompt_config["similarity_threshold"]:
        prompt_config["similarity_threshold"] = default_prompt["similarity_threshold"]

    if 'top_n' not in prompt_config or not prompt_config["top_n"]:
        prompt_config["top_n"] = default_prompt["top_n"]

    for p in prompt_config["parameters"]:
        if p["optional"]:
            continue
        if prompt_config["system"].find("{%s}" % p["key"]) < 0:
            return get_data_error_result(
                message="Parameter '{}' is not used".format(p["key"]))
    logging.info("prompt_config: %s",prompt_config)
    logging.info("prompt_config")
    try:
        tenant_id = UserTenantService.get_tenants_by_user_id(current_user.id)[0]['tenant_id']
        # logging.info("current_user.id:%s",current_user.id)
        # logging.info("tenant.id:%s",tenant_id)

        e, tenant = TenantService.get_by_id(current_user.id)
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            return get_data_error_result(message="Tenant not found!")
        kbs = KnowledgebaseService.get_by_ids(req.get("kb_ids", []))
        embd_ids = [TenantLLMService.split_model_name_and_factory(kb.embd_id)[0] for kb in kbs]  # remove vendor suffix for comparison
        embd_count = len(set(embd_ids))
        if embd_count > 1:
            return get_data_error_result(message=f'Datasets use different embedding models: {[kb.embd_id for kb in kbs]}"')

        llm_id = req.get("llm_id", tenant.llm_id)
        if not dialog_id:

            dia = {
                "id": get_uuid(),
                "tenant_id": tenant_id, # current_user.id,
                "name": name,
                "kb_ids": req.get("kb_ids", []),
                "description": description,
                "llm_id": llm_id,
                "llm_setting": llm_setting,
                "prompt_config": prompt_config,
                "top_n": top_n,
                "top_k": top_k,
                "rerank_id": rerank_id,
                "similarity_threshold": similarity_threshold,
                "vector_similarity_weight": vector_similarity_weight,
                "icon": icon
            }
            if not DialogService.save(**dia):
                return get_data_error_result(message="Fail to new a dialog!")
            return get_json_result(data=dia)
        else:
            del req["dialog_id"]
            if "kb_names" in req:
                del req["kb_names"]
            if not DialogService.update_by_id(dialog_id, req):
                return get_data_error_result(message="Dialog not found!")
            e, dia = DialogService.get_by_id(dialog_id)
            if not e:
                return get_data_error_result(message="Fail to update a dialog!")
            dia = dia.to_dict()
            dia.update(req)
            dia["kb_ids"], dia["kb_names"] = get_kb_names(dia["kb_ids"])
            return get_json_result(data=dia)
    except Exception as e:
        return server_error_response(e)


@manager.route('/get', methods=['GET'])  # noqa: F821
@login_required
def get():
    dialog_id = request.args["dialog_id"]
    # logging.info("!!!dialog_id!!!!:%s", dialog_id)
    try:
        e, dia = DialogService.get_by_id(dialog_id)
        
        if not e:
            return get_data_error_result(message="Dialog not found!")
        dia = dia.to_dict()
        
        dia["kb_ids"], dia["kb_names"] = get_kb_names(dia["kb_ids"])
        # logging.info("!!! return dia!!!!:%s", dia)
        return get_json_result(data=dia)
    except Exception as e:
        return server_error_response(e)


def get_kb_names(kb_ids):
    ids, nms = [], []
    for kid in kb_ids:
        e, kb = KnowledgebaseService.get_by_id(kid)
        if not e or kb.status != StatusEnum.VALID.value:
            continue
        ids.append(kid)
        nms.append(kb.name)
    return ids, nms


@manager.route('/list', methods=['GET'])  # noqa: F821
@login_required
def list_dialogs():
    # logging.info("!!!list_dialog!!!!:%s", current_user.id)
    tenant_id = UserTenantService.get_tenants_by_user_id(current_user.id)[0]['tenant_id']
    # logging.info("tenant.id:%s",tenant_id)
    try:
        diags = DialogService.query(
            tenant_id=tenant_id, #current_user.id,
            status=StatusEnum.VALID.value,
            reverse=True,
            order_by=DialogService.model.create_time)
        diags = [d.to_dict() for d in diags]
        # logging.info("!!!diags!!!!:%s",len(diags))
        # logging.info("!!!diags!!!!:%s",diags)
        for d in diags:
            d["kb_ids"], d["kb_names"] = get_kb_names(d["kb_ids"])
        return get_json_result(data=diags)
    except Exception as e:
        return server_error_response(e)


@manager.route('/rm', methods=['POST'])  # noqa: F821
@login_required
@validate_request("dialog_ids")
def rm():
    # logging.info("!!!conversation rm!!!!")
    req = request.json
    dialog_list=[]
    tenants = UserTenantService.query(user_id=current_user.id)
    try:
        for id in req["dialog_ids"]:
            for tenant in tenants:
                if DialogService.query(tenant_id=tenant.tenant_id, id=id):
                    break
            else:
                return get_json_result(
                    data=False, message='Only owner of dialog authorized for this operation.',
                    code=settings.RetCode.OPERATING_ERROR)
            dialog_list.append({"id": id,"status":StatusEnum.INVALID.value})
        DialogService.update_many_by_id(dialog_list)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)
