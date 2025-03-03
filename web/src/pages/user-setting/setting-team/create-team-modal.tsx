import teamService from '@/services/team-service';
import { Button, Form, Input, Modal, Typography, message } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;

interface CreateTeamModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateTeamModal = ({
  visible,
  onClose,
  onSuccess,
}: CreateTeamModalProps) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      console.log('Creating team with data:', values);
      const response = await teamService.createTeam({
        name: values.name,
      });

      console.log('Server response:', response);

      if (response?.data?.code === 0) {
        message.success(t('setting.createTeamSuccess'));
        form.resetFields();
        onSuccess();
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      } else {
        message.error(response?.data?.message || t('setting.createTeamFailed'));
      }
    } catch (error: any) {
      console.error('Create team failed:', error);
      if (error.response) {
        console.error('Error response:', error.response);
      }
      message.error(error.message || t('setting.createTeamFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={t('setting.createTeamTitle')}
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={loading}
      okText={t('common.create')}
      cancelText={t('common.cancel')}
      footer={[
        <Button
          key="submit"
          type="primary"
          loading={loading}
          onClick={handleSubmit}
        >
          {t('common.create')}
        </Button>,
        <Button key="cancel" onClick={onClose}>
          {t('common.cancel')}
        </Button>,
      ]}
      destroyOnClose
    >
      <Text
        style={{
          display: 'block',
          marginBottom: 16,
          color: '#ff4d4f',
          fontSize: '15px',
        }}
      >
        {t('setting.createTeamTip')}
      </Text>
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label={t('setting.teamName')}
          rules={[{ required: true, message: t('setting.teamNameRequired') }]}
        >
          <Input placeholder={t('common.pleaseInput')} />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateTeamModal;
