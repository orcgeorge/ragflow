import api from '@/utils/api';
import registerServer from '@/utils/register-server';
import request, { post } from '@/utils/request';

const {
  createTenant,
  listTenant,
  addTenantUser,
  listTenantUser,
  deleteTenantUser,
  agreeTenant,
  allTeams,
  teamMembers,
  handleApplication: handleApplicationApi,
} = api;

const methods = {
  createTeam: {
    url: createTenant,
    method: 'post',
  },
  listTeam: {
    url: listTenant,
    method: 'get',
  },
  listAllTeams: {
    url: allTeams,
    method: 'get',
  },
} as const;

const teamService = registerServer<keyof typeof methods>(methods, request);

export const addTeamUser = (tenantId: string, email: string) =>
  post(addTenantUser(tenantId), { email });

export const listTeamUsers = (tenantId: string) =>
  request.get(listTenantUser(tenantId));

export const deleteTeamUser = ({
  tenantId,
  userId,
}: {
  tenantId: string;
  userId: string;
}) => request.delete(deleteTenantUser(tenantId, userId));

export const agreeTeam = (tenantId: string) =>
  request.put(agreeTenant(tenantId));

export const getTeamMembers = (tenantId: string) =>
  request.get(teamMembers(tenantId));

export const applyTeam = (tenantId: string) =>
  request.post(`/v1/tenant/${tenantId}/apply`);

export const handleApplication = (
  tenantId: string,
  userId: string,
  action: 'accept' | 'reject',
) =>
  request.post(handleApplicationApi(tenantId), {
    data: { user_id: userId, action },
    skipTransform: true,
  });

export default teamService;
