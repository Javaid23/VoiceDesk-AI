"use client";

import { useEffect } from "react";
import { useRoomContext } from "@livekit/components-react";

export function RpcHandlers() {
  const room = useRoomContext();

  useEffect(() => {
    if (!room) return;

    const handleShowNotification = async (data: any): Promise<string> => {
      try {
        if (!data || data.payload === undefined) {
          return "Error: Invalid RPC data format";
        }
        const payload = typeof data.payload === "string" ? JSON.parse(data.payload) : data.payload;
        const notificationType = payload?.type;

        if (typeof notificationType !== "string" || notificationType.trim() === "") {
          return "Error: Invalid or missing notification type";
        }

        // Wait function
        const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
        
        // Wait 3 seconds before showing popup
        await wait(3000);
        
        // Create and show popup based on notification type
        const popup = document.createElement("div");
        let message = "";
        let backgroundColor = "#10b981"; // Default green
        
        if (notificationType === "unblock_user") {
          const username = payload?.username;
          if (typeof username !== "string" || username.trim() === "") {
            return "Error: Invalid or missing username for unblock_user notification";
          }
          message = `User ${username} was unblocked!`;
          backgroundColor = "#10b981"; // Green
        } else if (notificationType === "send_email") {
          const emailAddress = payload?.email_address;
          if (typeof emailAddress !== "string" || emailAddress.trim() === "") {
            return "Error: Invalid or missing email_address for send_email notification";
          }
          message = `Successfully sent email to ${emailAddress}`;
          backgroundColor = "#3b82f6"; // Blue
        } else {
          return "Error: Unknown notification type";
        }
        
        popup.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          background: ${backgroundColor};
          color: white;
          padding: 16px 24px;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          z-index: 10000;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 14px;
          font-weight: 500;
          max-width: 300px;
          animation: slideIn 0.3s ease-out;
        `;
        
        // Add CSS animation
        const style = document.createElement("style");
        style.textContent = `
          @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
          }
        `;
        document.head.appendChild(style);
        
        popup.textContent = message;
        document.body.appendChild(popup);

        // Auto-remove after 10 seconds
        setTimeout(() => {
          if (popup.parentNode) {
            popup.style.animation = "slideIn 0.3s ease-out reverse";
            setTimeout(() => {
              if (popup.parentNode) {
                popup.parentNode.removeChild(popup);
              }
            }, 300);
          }
        }, 10000);

        return "Notification shown";
      } catch (err) {
        return "Error: " + (err instanceof Error ? err.message : String(err));
      }
    };

    room.localParticipant.registerRpcMethod("client.showNotification", handleShowNotification);

    return () => {
      room.localParticipant.unregisterRpcMethod("client.showNotification");
    };
  }, [room]);

  return null;
}