import { useFetchUserInfo, useListTenant } from '@/hooks/user-setting-hooks';
import { PlusOutlined, TeamOutlined } from '@ant-design/icons';
import { Button, Card, Space, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TenantRole } from '../constants';
import AllTeamsTable from './all-teams-table';
import CreateTeamModal from './create-team-modal';
import styles from './index.less';
import MyTeamMembersTable from './my-team-members-table';
import TenantTable from './tenant-table';

const { Text } = Typography;
const iconStyle = { fontSize: 20, color: '#1677ff' };

const UserSettingTeam = () => {
  const { data: userInfo } = useFetchUserInfo();
  const { data: tenants } = useListTenant();
  const { t } = useTranslation();
  const [createModalVisible, setCreateModalVisible] = useState(false);

  // 找到用户创建的团队
  const ownerTeam = tenants?.find((team) => team.role === TenantRole.Owner);

  const handleCreateSuccess = () => {
    setCreateModalVisible(false);
    // 刷新团队列表
  };

  return (
    <div className={styles.teamWrapper}>
      <Card
        title={
          <Space>
            <TeamOutlined style={iconStyle} />
            <Text>{t('setting.allTeams')}</Text>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            {t('setting.createTeam')}
          </Button>
        }
        bordered={false}
      >
        <AllTeamsTable />
      </Card>

      {ownerTeam && (
        <Card
          title={
            <Space>
              <TeamOutlined style={iconStyle} /> {t('setting.myTeamManagement')}
            </Space>
          }
          bordered={false}
        >
          <MyTeamMembersTable
            tenantId={ownerTeam.tenant_id}
            currentUserId={userInfo?.id || ''}
          />
        </Card>
      )}

      <Card
        title={
          <Space>
            <TeamOutlined style={iconStyle} /> {t('setting.joinedTeams')}
          </Space>
        }
        bordered={false}
      >
        <TenantTable />
      </Card>

      <CreateTeamModal
        visible={createModalVisible}
        onClose={() => setCreateModalVisible(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
};

export default UserSettingTeam;
