import {
  deleteTeamUser,
  getTeamMembers,
  handleApplication,
} from '@/services/team-service';
import { formatDate } from '@/utils/date';
import { DeleteOutlined } from '@ant-design/icons';
import type { TableProps } from 'antd';
import { Button, Space, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IMember {
  user_id: string;
  nickname: string;
  email: string;
  role: string;
  join_date: string;
  update_date: string;
}

interface MyTeamMembersTableProps {
  tenantId: string;
  currentUserId: string;
}

const MyTeamMembersTable = ({
  tenantId,
  currentUserId,
}: MyTeamMembersTableProps) => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [members, setMembers] = useState<IMember[]>([]);

  const fetchMembers = async () => {
    try {
      setLoading(true);
      const response = await getTeamMembers(tenantId);
      if (response?.data?.code === 0) {
        setMembers(response.data.data || []);
      } else {
        message.error(
          response?.data?.message || t('setting.fetchMembersFailed'),
        );
      }
    } catch (error: any) {
      console.error('Fetch members failed:', error);
      message.error(error.message || t('setting.fetchMembersFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tenantId) {
      fetchMembers();
    }
  }, [tenantId]);

  const handleRemoveMember = async (userId: string) => {
    try {
      const response = await deleteTeamUser({
        tenantId,
        userId,
      });
      if (response?.data?.code === 0) {
        message.success(t('setting.removeMemberSuccess'));
        fetchMembers(); // 刷新列表
      } else {
        message.error(
          response?.data?.message || t('setting.removeMemberFailed'),
        );
      }
    } catch (error: any) {
      console.error('Remove member failed:', error);
      message.error(error.message || t('setting.removeMemberFailed'));
    }
  };

  const handleAcceptMember = async (userId: string) => {
    try {
      console.log('Accepting member:', { tenantId, userId });
      const response = await handleApplication(tenantId, userId, 'accept');
      console.log('Accept response:', response);
      if (response?.data?.code === 0) {
        message.success(t('setting.acceptMemberSuccess'));
        fetchMembers(); // 刷新列表
      } else {
        message.error(
          response?.data?.message || t('setting.acceptMemberFailed'),
        );
      }
    } catch (error: any) {
      console.error('Accept member failed:', error);
      message.error(error.message || t('setting.acceptMemberFailed'));
    }
  };

  const handleRejectMember = async (userId: string) => {
    try {
      console.log('Rejecting member:', { tenantId, userId });
      const response = await handleApplication(tenantId, userId, 'reject');
      console.log('Reject response:', response);
      if (response?.data?.code === 0) {
        message.success(t('setting.rejectMemberSuccess'));
        fetchMembers(); // 刷新列表
      } else {
        message.error(
          response?.data?.message || t('setting.rejectMemberFailed'),
        );
      }
    } catch (error: any) {
      console.error('Reject member failed:', error);
      message.error(error.message || t('setting.rejectMemberFailed'));
    }
  };

  const columns: TableProps<IMember>['columns'] = [
    {
      title: t('common.name'),
      dataIndex: 'nickname',
      key: 'nickname',
    },
    {
      title: t('setting.email'),
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: t('setting.role'),
      dataIndex: 'role',
      key: 'role',
      render: (role) => (
        <Tag
          color={
            role === 'pending' ? 'orange' : role === 'owner' ? 'gold' : 'green'
          }
        >
          {role === 'pending'
            ? t('setting.pending')
            : role === 'owner'
              ? t('setting.owner')
              : t('setting.member')}
        </Tag>
      ),
    },
    {
      title: t('setting.joinDate'),
      dataIndex: 'join_date',
      key: 'join_date',
      render: (value) => formatDate(value),
    },
    {
      title: t('common.action'),
      key: 'action',
      render: (_, record) => {
        // 如果是创建者，不显示任何操作按钮
        if (record.role === 'owner') {
          return null;
        }

        // 如果是待审核的成员
        if (record.role === 'pending') {
          return (
            <Space>
              <Button
                type="link"
                onClick={() => handleAcceptMember(record.user_id)}
              >
                {t('setting.accept')}
              </Button>
              <Button
                type="link"
                danger
                onClick={() => handleRejectMember(record.user_id)}
              >
                {t('setting.reject')}
              </Button>
            </Space>
          );
        }

        // 如果是普通成员，显示删除按钮
        return (
          <Button
            type="text"
            danger
            onClick={() => handleRemoveMember(record.user_id)}
          >
            <DeleteOutlined />
          </Button>
        );
      },
    },
  ];

  return (
    <Table<IMember>
      columns={columns}
      dataSource={members}
      rowKey="user_id"
      pagination={false}
      loading={loading}
    />
  );
};

export default MyTeamMembersTable;
