import NotificationList from "../components/NotificationList";
import { PageHeader, Card, Breadcrumb } from "../components/ui";

function Notifications() {
  return (
    <>
      <Breadcrumb
        items={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Notifications" },
        ]}
      />

      <PageHeader
        title="Notifications"
        description="Everything that happened on your travel requests."
      />

      <Card padded={false}>
        <NotificationList />
      </Card>
    </>
  );
}

export default Notifications;
