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
import hashlib
from datetime import datetime

import peewee
from werkzeug.security import generate_password_hash, check_password_hash

from api.db import UserTenantRole, StatusEnum
from api.db.db_models import DB, UserTenant, User, Tenant
from api.db.services.common_service import CommonService
from api.utils import get_uuid, current_timestamp, datetime_format
from rag.settings import MINIO


class UserService(CommonService):
    model = User

    @classmethod
    @DB.connection_context()
    def filter_by_id(cls, user_id):
        try:
            user = cls.model.select().where(cls.model.id == user_id).get()
            return user
        except peewee.DoesNotExist:
            return None

    @classmethod
    @DB.connection_context()
    def query_user(cls, email, password):
        user = cls.model.select().where((cls.model.email == email),
                                        (cls.model.status == StatusEnum.VALID.value)).first()
        if user and check_password_hash(str(user.password), password):
            return user
        else:
            return None

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = get_uuid()
        if "password" in kwargs:
            kwargs["password"] = generate_password_hash(
                str(kwargs["password"]))

        kwargs["create_time"] = current_timestamp()
        kwargs["create_date"] = datetime_format(datetime.now())
        kwargs["update_time"] = current_timestamp()
        kwargs["update_date"] = datetime_format(datetime.now())
        obj = cls.model(**kwargs).save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def delete_user(cls, user_ids, update_user_dict):
        with DB.atomic():
            cls.model.update({"status": 0}).where(
                cls.model.id.in_(user_ids)).execute()

    @classmethod
    @DB.connection_context()
    def update_user(cls, user_id, user_dict):
        with DB.atomic():
            if user_dict:
                user_dict["update_time"] = current_timestamp()
                user_dict["update_date"] = datetime_format(datetime.now())
                cls.model.update(user_dict).where(
                    cls.model.id == user_id).execute()


class TenantService(CommonService):
    model = Tenant

    @classmethod
    @DB.connection_context()
    def get_info_by(cls, user_id):
        fields = [
            cls.model.id.alias("tenant_id"),
            cls.model.name,
            cls.model.llm_id,
            cls.model.embd_id,
            cls.model.rerank_id,
            cls.model.asr_id,
            cls.model.img2txt_id,
            cls.model.tts_id,
            cls.model.parser_ids,
            UserTenant.role]
        return list(cls.model.select(*fields)
                    .join(UserTenant, on=((cls.model.id == UserTenant.tenant_id) & (UserTenant.user_id == user_id) & (UserTenant.status == StatusEnum.VALID.value) & (UserTenant.role == UserTenantRole.OWNER)))
                    .where(cls.model.status == StatusEnum.VALID.value).dicts())

    @classmethod
    @DB.connection_context()
    def get_joined_tenants_by_user_id(cls, user_id):
        fields = [
            cls.model.id.alias("tenant_id"),
            cls.model.name,
            cls.model.llm_id,
            cls.model.embd_id,
            cls.model.asr_id,
            cls.model.img2txt_id,
            UserTenant.role]
        return list(cls.model.select(*fields)
                    .join(UserTenant, on=((cls.model.id == UserTenant.tenant_id) & (UserTenant.user_id == user_id) & (UserTenant.status == StatusEnum.VALID.value) & (UserTenant.role == UserTenantRole.NORMAL)))
                    .where(cls.model.status == StatusEnum.VALID.value).dicts())
    
    @classmethod
    @DB.connection_context()
    def get_info_all(cls, user_id):
        fields = [
            cls.model.id.alias("tenant_id"),
            cls.model.name,
            cls.model.llm_id,
            cls.model.embd_id,
            cls.model.asr_id,
            cls.model.img2txt_id,
            UserTenant.role]
        return list(cls.model.select(*fields)
                    .join(UserTenant, on=((cls.model.id == UserTenant.tenant_id) & (UserTenant.user_id == user_id) & (UserTenant.status == StatusEnum.VALID.value) ))
                    .where(cls.model.status == StatusEnum.VALID.value).dicts())
    
    @classmethod
    @DB.connection_context()
    def decrease(cls, user_id, num):
        num = cls.model.update(credit=cls.model.credit - num).where(
            cls.model.id == user_id).execute()
        if num == 0:
            raise LookupError("Tenant not found which is supposed to be there")

    @classmethod
    @DB.connection_context()
    def user_gateway(cls, tenant_id):
        hashobj = hashlib.sha256(tenant_id.encode("utf-8"))
        return int(hashobj.hexdigest(), 16)%len(MINIO)


class UserTenantService(CommonService):
    model = UserTenant

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = get_uuid()
        obj = cls.model(**kwargs).save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def get_by_tenant_id(cls, tenant_id):
        import logging
        fields = [
            cls.model.user_id,
            cls.model.status,
            cls.model.role,
            cls.model.create_date.alias("join_date"),
            User.nickname,
            User.email,
            User.avatar,
            User.is_authenticated,
            User.is_active,
            User.is_anonymous,
            User.status,
            User.update_date,
            User.is_superuser]
            
        query = cls.model.select(*fields)\
            .join(User, on=((cls.model.user_id == User.id) & (cls.model.status == StatusEnum.VALID.value)))\
            .where(
                (cls.model.tenant_id == tenant_id) &
                (cls.model.role.in_([UserTenantRole.NORMAL.value, UserTenantRole.INVITE.value, UserTenantRole.PENDING.value]))
            )
            
        logging.info(f"Get team members SQL Query: {query.sql()}")
        result = list(query.dicts())
        logging.info(f"Team members result: {result}")
        return result

    @classmethod
    @DB.connection_context()
    def get_tenants_by_user_id(cls, user_id):
        import logging
        fields = [
            Tenant.id.alias("tenant_id"),
            Tenant.name,
            cls.model.role,
            Tenant.llm_id,
            Tenant.embd_id,
            Tenant.asr_id,
            Tenant.img2txt_id,
            User.nickname.alias("owner_name"),
            User.email.alias("owner_email"),
            Tenant.create_date,
            Tenant.update_date
        ]
        
        # 先找到每个团队的所有者信息
        owner_subquery = cls.model.select(
            cls.model.tenant_id,
            cls.model.user_id.alias('owner_id')
        ).where(cls.model.role == UserTenantRole.OWNER.value)
        
        query = cls.model.select(*fields)\
            .join(Tenant, on=(cls.model.tenant_id == Tenant.id))\
            .join(owner_subquery, on=(Tenant.id == owner_subquery.c.tenant_id))\
            .join(User, on=(User.id == owner_subquery.c.owner_id))\
            .where(
                (cls.model.user_id == user_id) &
                (cls.model.status == StatusEnum.VALID.value) &
                (Tenant.status == StatusEnum.VALID.value)
            )
        
        logging.info(f"SQL Query: {query.sql()}")
        result = list(query.dicts())
        logging.info(f"Query result: {result}")
        
        # 特殊处理 VC_ALL 团队的所有者信息
        for team in result:
            if team["tenant_id"] == "VC_ALL":
                team["owner_name"] = "System"
                team["owner_email"] = "system@infiniflow.ai"
        
        return result

    @classmethod
    @DB.connection_context()
    def get_all_available_teams(cls, user_id):
        """获取所有可加入的团队列表（包含申请状态）"""
        import logging
        fields = [
            Tenant.id.alias("tenant_id"),
            Tenant.name,
            User.nickname.alias("owner_name"),
            User.email.alias("owner_email"),
            Tenant.create_date,
            Tenant.update_date
        ]
        
        # 获取用户已加入的团队ID（NORMAL和OWNER角色）
        joined_query = (UserTenant
                       .select(UserTenant.tenant_id)
                       .where(
                           (UserTenant.user_id == user_id) &
                           (UserTenant.role.in_([UserTenantRole.NORMAL.value, UserTenantRole.OWNER.value]))
                       ))
        logging.info(f"Get joined teams SQL Query: {joined_query.sql()}")
        joined_teams = joined_query.tuples()
        logging.info(f"Joined teams result: {joined_teams}")
        
        # 查询所有可见的团队
        teams_query = (Tenant
                   .select(*fields)
                   .join(UserTenant, on=(Tenant.id == UserTenant.tenant_id))
                   .join(User, on=(UserTenant.user_id == User.id))
                   .where(
                       (Tenant.status == StatusEnum.VALID.value) &
                       (UserTenant.role == UserTenantRole.OWNER.value) &
                       (~(Tenant.id << joined_teams))
                   ))
        logging.info(f"Get available teams SQL Query: {teams_query.sql()}")
        teams = list(teams_query.dicts())
        logging.info(f"Available teams result: {teams}")
                   
        # 获取用户的申请状态
        pending_query = (UserTenant
                          .select(UserTenant.tenant_id)
                          .where(
                              (UserTenant.user_id == user_id) &
                              (UserTenant.role == UserTenantRole.PENDING.value)
                          ))
        logging.info(f"Get pending teams SQL Query: {pending_query.sql()}")
        pending_teams = set(pending_query.tuples())
        logging.info(f"Pending teams result: {pending_teams}")
                          
        # 添加申请状态
        for team in teams:
            team["has_applied"] = (team["tenant_id"],) in pending_teams
            
        return teams

    @classmethod
    @DB.connection_context()
    def create_tenant(cls, tenant_data):
        """创建新团队"""
        tenant_data.update({
            "create_time": current_timestamp(),
            "create_date": datetime_format(datetime.now()),
            "update_time": current_timestamp(),
            "update_date": datetime_format(datetime.now())
        })
        return Tenant.create(**tenant_data)

    @classmethod
    @DB.connection_context()
    def is_owner(cls, user_id, tenant_id):
        """检查用户是否是团队所有者"""
        try:
            return cls.model.get(
                (cls.model.user_id == user_id) &
                (cls.model.tenant_id == tenant_id) &
                (cls.model.role == UserTenantRole.OWNER) &
                (cls.model.status == StatusEnum.VALID.value)
            )
        except peewee.DoesNotExist:
            return None

    @classmethod
    @DB.connection_context()
    def get_all_members(cls, tenant_id):
        """获取团队所有成员（包括待审核的）"""
        import logging
        fields = [
            User.id.alias("user_id"),
            User.nickname,
            User.email,
            User.avatar,
            cls.model.role,
            cls.model.create_date.alias("join_date"),
            User.update_date,
            Tenant.name.alias("tenant_name")
        ]
        
        query = User.select(*fields)\
                   .join(cls.model, on=(User.id == cls.model.user_id))\
                   .join(Tenant, on=(cls.model.tenant_id == Tenant.id))\
                   .where(
                       (cls.model.tenant_id == tenant_id) &
                       (cls.model.status == StatusEnum.VALID.value)
                   )
                   
        logging.info(f"Get all members SQL Query: {query.sql()}")
        result = list(query.dicts())
        logging.info(f"Get all members result: {result}")
        return result

    @classmethod
    @DB.connection_context()
    def get_pending_members(cls, tenant_id):
        """获取待审核的成员列表"""
        fields = [
            User.id.alias("user_id"),
            User.nickname,
            User.email,
            User.avatar,
            cls.model.create_date.alias("apply_date"),
            User.update_date
        ]
        
        return list(User
                   .select(*fields)
                   .join(cls.model, on=(User.id == cls.model.user_id))
                   .where(
                       (cls.model.tenant_id == tenant_id) &
                       (cls.model.status == StatusEnum.VALID.value) &
                       (cls.model.role == UserTenantRole.PENDING)
                   ).dicts())

    @classmethod
    @DB.connection_context()
    def handle_application(cls, tenant_id, user_id, accept=True):
        """处理成员申请"""
        with DB.atomic():
            if accept:
                cls.model.update(
                    role=UserTenantRole.NORMAL,
                    update_time=current_timestamp(),
                    update_date=datetime_format(datetime.now())
                ).where(
                    (cls.model.tenant_id == tenant_id) &
                    (cls.model.user_id == user_id) &
                    (cls.model.role == UserTenantRole.PENDING)
                ).execute()
            else:
                cls.model.delete().where(
                    (cls.model.tenant_id == tenant_id) &
                    (cls.model.user_id == user_id) &
                    (cls.model.role == UserTenantRole.PENDING)
                ).execute()
