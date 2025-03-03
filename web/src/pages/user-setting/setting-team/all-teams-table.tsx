import teamService, { applyTeam } from '@/services/team-service';
import { formatDate } from '@/utils/date';
import type { TableProps } from 'antd';
import { Button, Table, message } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface ITeam {
  tenant_id: string;
  name: string;
  owner_name: string;
  owner_email: string;
  create_date: string;
  update_date: string;
  has_applied: boolean;
}

const AllTeamsTable = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [teams, setTeams] = useState<ITeam[]>([]);

  const fetchTeams = async () => {
    try {
      setLoading(true);
      const response = await teamService.listAllTeams();
      if (response?.data?.code === 0) {
        setTeams(response.data.data || []);
      } else {
        message.error(response?.data?.message || t('setting.fetchTeamsFailed'));
      }
    } catch (error: any) {
      console.error('Fetch teams failed:', error);
      message.error(error.message || t('setting.fetchTeamsFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const handleApply = async (teamId: string) => {
    try {
      const response = await applyTeam(teamId);
      if (response?.data?.code === 0) {
        message.success(t('setting.applySuccess'));
        fetchTeams(); // 刷新列表
      } else {
        message.error(response?.data?.message || t('setting.applyFailed'));
      }
    } catch (error: any) {
      console.error('Apply team failed:', error);
      message.error(error.message || t('setting.applyFailed'));
    }
  };

  const columns: TableProps<ITeam>['columns'] = [
    {
      title: t('common.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('setting.owner'),
      dataIndex: 'owner_name',
      key: 'owner_name',
      render: (value, record) => `${value} (${record.owner_email})`,
    },
    {
      title: t('setting.createDate'),
      dataIndex: 'create_date',
      key: 'create_date',
      render: (value) => formatDate(value),
    },
    {
      title: t('common.action'),
      key: 'action',
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => handleApply(record.tenant_id)}
          disabled={record.has_applied}
        >
          {record.has_applied ? t('setting.applied') : t('setting.applyJoin')}
        </Button>
      ),
    },
  ];

  return (
    <Table<ITeam>
      columns={columns}
      dataSource={teams}
      rowKey="tenant_id"
      pagination={false}
      loading={loading}
    />
  );
};

export default AllTeamsTable;
