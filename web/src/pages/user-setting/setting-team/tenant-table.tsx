import { useFetchUserInfo, useListTenant2 } from '@/hooks/user-setting-hooks';
import { ITenant } from '@/interfaces/database/user-setting';
import type { TableProps } from 'antd';
import { Button, Space, Table, Tag } from 'antd';
import { useTranslation } from 'react-i18next';
import { TenantRole } from '../constants';
import { useHandleAgreeTenant, useHandleQuitUser } from './hooks';

interface TenantTableProps {
  onTeamSelect?: (teamId: string) => void;
}

const TenantTable = ({ onTeamSelect }: TenantTableProps) => {
  const { t } = useTranslation();
  const { data, loading } = useListTenant2();
  const { handleAgree } = useHandleAgreeTenant();
  const { data: user } = useFetchUserInfo();
  const { handleQuitTenantUser } = useHandleQuitUser();

  const columns: TableProps<ITenant>['columns'] = [
    {
      title: t('common.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('setting.role'),
      dataIndex: 'role',
      key: 'role',
      render: (role) => (
        <Tag color={role === TenantRole.Owner ? 'gold' : 'green'}>
          {role === TenantRole.Owner ? t('setting.owner') : t('setting.member')}
        </Tag>
      ),
    },
    {
      title: t('setting.owner'),
      dataIndex: 'owner_name',
      key: 'owner_name',
      render: (value, record) => `${value} (${record.owner_email})`,
    },
    {
      title: t('common.action'),
      key: 'action',
      render: (_, { role, tenant_id }) => {
        if (role === TenantRole.Invite) {
          return (
            <Space>
              <Button type="link" onClick={handleAgree(tenant_id, true)}>
                {t(`setting.agree`)}
              </Button>
              <Button type="link" onClick={handleAgree(tenant_id, false)}>
                {t(`setting.refuse`)}
              </Button>
            </Space>
          );
        } else if (role === TenantRole.Normal && user.id !== tenant_id) {
          return (
            <Button
              type="link"
              onClick={handleQuitTenantUser(user.id, tenant_id)}
            >
              {t('setting.quit')}
            </Button>
          );
        }
        return null;
      },
    },
  ];

  return (
    <Table<ITenant>
      columns={columns}
      dataSource={data}
      rowKey={'tenant_id'}
      loading={loading}
      pagination={false}
      onRow={(record) => ({
        onClick: () => onTeamSelect?.(record.tenant_id),
      })}
    />
  );
};

export default TenantTable;
