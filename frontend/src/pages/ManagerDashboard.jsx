import { useNavigate } from "react-router-dom";

import NotificationList from "../components/NotificationList";

function ManagerDashboard() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        maxWidth: "1100px",
        margin: "40px auto",
        padding: "20px",
      }}
    >
      <div
        style={{
          background: "#ffffff",
          border: "1px solid #ddd",
          borderRadius: "10px",
          padding: "30px",
        }}
      >
        <h1
          style={{
            marginTop: 0,
          }}
        >
          Manager Dashboard
        </h1>

        <p>
          Review employee travel requests and make
          the final travel-request decision.
        </p>

        <hr />

        <div
          style={{
            display: "flex",
            gap: "20px",
            marginTop: "25px",
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              flex: "1 1 220px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              padding: "20px",
            }}
          >
            <h3>Travel Requests</h3>

            <p>
              View travel requests submitted by
              employees in your team.
            </p>

            <button
              onClick={() =>
                navigate("/manager/travel-requests")
              }
            >
              View Travel Requests
            </button>
          </div>

          <div
            style={{
              flex: "1 1 220px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              padding: "20px",
            }}
          >
            <h3>Document Verification</h3>

            <p>
              Review the document verification
              status before making a final decision.
            </p>
          </div>
        </div>

        <NotificationList />
      </div>
    </div>
  );
}

export default ManagerDashboard;