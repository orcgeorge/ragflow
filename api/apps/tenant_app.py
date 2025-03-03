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

from flask import request, Blueprint
from flask_login import login_required, current_user
from datetime import datetime
import logging

from api import settings
from api.db import UserTenantRole, StatusEnum
from api.db.db_models import UserTenant, Tenant
from api.db.services.user_service import UserTenantService, UserService
from api.db.services.llm_service import LLMService, TenantLLMService

from api.utils import get_uuid, delta_seconds, current_timestamp, datetime_format
from api.utils.api_utils import get_json_result, validate_request, server_error_response, get_data_error_result

manager = Blueprint('tenant', __name__)


@manager.route("/<tenant_id>/user/list", methods=["GET"])  # noqa: F821
@login_required
def user_list(tenant_id):
    if not UserTenantService.is_owner(current_user.id, tenant_id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR)

    try:
        users = UserTenantService.get_by_tenant_id(tenant_id)
        for u in users:
            u["delta_seconds"] = delta_seconds(str(u["update_date"]))
        return get_json_result(data=users)
    except Exception as e:
        return server_error_response(e)


@manager.route('/<tenant_id>/user', methods=['POST'])  # noqa: F821
@login_required
@validate_request("email")
def create(tenant_id):
    if not UserTenantService.is_owner(current_user.id, tenant_id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR)

    req = request.json
    invite_user_email = req["email"]
    invite_users = UserService.query(email=invite_user_email)
    if not invite_users:
        return get_data_error_result(message="User not found.")

    user_id_to_invite = invite_users[0].id
    user_tenants = UserTenantService.query(user_id=user_id_to_invite, tenant_id=tenant_id)
    if user_tenants:
        user_tenant_role = user_tenants[0].role
        if user_tenant_role == UserTenantRole.NORMAL:
            return get_data_error_result(message=f"{invite_user_email} is already in the team.")
        if user_tenant_role == UserTenantRole.OWNER:
            return get_data_error_result(message=f"{invite_user_email} is the owner of the team.")
        return get_data_error_result(message=f"{invite_user_email} is in the team, but the role: {user_tenant_role} is invalid.")

    UserTenantService.save(
        id=get_uuid(),
        user_id=user_id_to_invite,
        tenant_id=tenant_id,
        invited_by=current_user.id,
        role=UserTenantRole.INVITE,
        status=StatusEnum.VALID.value)

    usr = invite_users[0].to_dict()
    usr = {k: v for k, v in usr.items() if k in ["id", "avatar", "email", "nickname"]}

    return get_json_result(data=usr)


@manager.route('/<tenant_id>/user/<user_id>', methods=['DELETE'])  # noqa: F821
@login_required
def rm(tenant_id, user_id):
    # 允许团队所有者或用户自己删除
    if not (UserTenantService.is_owner(current_user.id, tenant_id) or current_user.id == user_id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR)

    try:
        UserTenantService.filter_delete([UserTenant.tenant_id == tenant_id, UserTenant.user_id == user_id])
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/list", methods=["GET"])  # noqa: F821
@login_required
def tenant_list():
    try:
        logging.info(f"Fetching tenant list for user: {current_user.id}")
        users = UserTenantService.get_tenants_by_user_id(current_user.id)
        logging.info(f"Found tenants: {users}")
        for u in users:
            u["delta_seconds"] = delta_seconds(str(u["update_date"]))
        return get_json_result(data=users)
    except Exception as e:
        logging.error(f"Error in tenant_list: {str(e)}")
        return server_error_response(e)


@manager.route("/agree/<tenant_id>", methods=["PUT"])  # noqa: F821
@login_required
def agree(tenant_id):
    try:
        UserTenantService.filter_update([UserTenant.tenant_id == tenant_id, UserTenant.user_id == current_user.id], {"role": UserTenantRole.NORMAL})
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/all", methods=["GET"])
@login_required
def all_teams():
    try:
        teams = UserTenantService.get_all_available_teams(current_user.id)
        for team in teams:
            team["delta_seconds"] = delta_seconds(str(team["update_date"]))
        return get_json_result(data=teams)
    except Exception as e:
        return server_error_response(e)


@manager.route("/create", methods=["POST"])
@login_required
@validate_request("name")
def create_team():
    """创建新团队
    每个用户只能创建一个团队
    """
    req = request.json
    try:
        # 检查用户是否已经是某个团队的所有者
        existing_teams = UserTenantService.query(
            user_id=current_user.id,
            role=UserTenantRole.OWNER,
            status=StatusEnum.VALID.value
        )
        if existing_teams:
            return get_json_result(
                data=False,
                message='每个用户只能创建一个团队',
                code=settings.RetCode.AUTHENTICATION_ERROR
            )

        tenant_id = get_uuid()
        tenant = {
            "id": tenant_id,
            "name": req["name"],
            "status": StatusEnum.VALID.value,
            "llm_id": settings.CHAT_MDL,
            "embd_id": settings.EMBEDDING_MDL,
            "asr_id": settings.ASR_MDL,
            "parser_ids": settings.PARSERS,
            "img2txt_id": settings.IMAGE2TEXT_MDL,
            "rerank_id": settings.RERANK_MDL,
            "create_time": current_timestamp(),
            "create_date": datetime_format(datetime.now()),
            "update_time": current_timestamp(),
            "update_date": datetime_format(datetime.now())
        }
        UserTenantService.create_tenant(tenant)
        
        UserTenantService.save(
            id=get_uuid(),
            user_id=current_user.id,
            tenant_id=tenant_id,
            invited_by=current_user.id,
            role=UserTenantRole.OWNER,
            status=StatusEnum.VALID.value
        )

        # 添加默认的LLM配置
        tenant_llm = []
        for llm in LLMService.query(fid=settings.LLM_FACTORY):
            tenant_llm.append({
                "tenant_id": tenant_id,
                "llm_factory": settings.LLM_FACTORY,
                "llm_name": llm.llm_name,
                "model_type": llm.model_type,
                "api_key": settings.API_KEY,
                "api_base": settings.LLM_BASE_URL,
                "max_tokens": llm.max_tokens if llm.max_tokens else 8192
            })
        TenantLLMService.insert_many(tenant_llm)

        return get_json_result(data=tenant)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<tenant_id>/apply", methods=["POST"])
@login_required
def apply_team(tenant_id):
    try:
        existing = UserTenantService.query(user_id=current_user.id, tenant_id=tenant_id)
        if existing:
            return get_data_error_result(message="You have already applied or joined this team.")
            
        UserTenantService.save(
            id=get_uuid(),
            user_id=current_user.id,
            tenant_id=tenant_id,
            role=UserTenantRole.PENDING.value,
            status=StatusEnum.VALID.value
        )
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<tenant_id>/handle_application", methods=["POST"])
@login_required
@validate_request("user_id", "action")
def handle_application(tenant_id):
    if not UserTenantService.is_owner(current_user.id, tenant_id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR)
    
    req = request.json
    user_id = req["user_id"]
    action = req["action"]
    
    try:
        if action == "accept":
            UserTenantService.filter_update(
                [UserTenant.tenant_id == tenant_id, UserTenant.user_id == user_id],
                {"role": UserTenantRole.NORMAL}
            )
        else:
            UserTenantService.filter_delete(
                [UserTenant.tenant_id == tenant_id, UserTenant.user_id == user_id]
            )
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<tenant_id>/members", methods=["GET"])
@login_required
def team_members(tenant_id):
    if not UserTenantService.is_owner(current_user.id, tenant_id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR)
            
    try:
        members = UserTenantService.get_all_members(tenant_id)
        return get_json_result(data=members)
    except Exception as e:
        return server_error_response(e)
