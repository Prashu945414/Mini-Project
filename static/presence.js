// Shared Socket.IO connection used across every page, plus simple
// online/offline indicator handling for any element carrying a
// data-username attribute (avatars, header status, sidebar rows).
//
// Pages that need the socket for their own events (chat.html) should reuse
// window.chatSocket instead of calling io() again, so there's only ever one
// connection per tab.

window.chatSocket = io();

function applyPresence(onlineUsernames) {
    const online = new Set(onlineUsernames || []);

    document.querySelectorAll("[data-username]").forEach((el) => {
        const name = el.dataset.username;
        const isOnline = online.has(name);

        el.classList.toggle("is-online", isOnline);
        el.classList.toggle("is-offline", !isOnline);

        const label = el.querySelector("[data-status-label]");
        if (label) {
            label.textContent = isOnline ? "Online" : "Offline";
        }
    });
}

window.chatSocket.on("presence_update", (data) => {
    applyPresence(data.online_users);
});

function updateUnreadBadge(contactUsername, unreadCount) {
    const row = Array.from(document.querySelectorAll("[data-contact-username]"))
        .find((element) => element.dataset.contactUsername === contactUsername);

    if (!row) return;

    row.dataset.unreadCount = unreadCount;
    row.classList.toggle("has-unread", unreadCount > 0);

    let badge = row.querySelector(".unread-badge");
    if (unreadCount > 0) {
        if (!badge) {
            badge = document.createElement("span");
            badge.className = "unread-badge";
            row.querySelector(".user-info").appendChild(badge);
        }
        badge.textContent = unreadCount > 99 ? "99+" : String(unreadCount);
        badge.setAttribute("aria-label", `${unreadCount} unread messages`);
    } else if (badge) {
        badge.remove();
    }
}

window.chatSocket.on("message_notification", (data) => {
    const row = Array.from(document.querySelectorAll("[data-contact-username]"))
        .find((element) => element.dataset.contactUsername === data.sender);

    if (!row) return;

    const preview = row.querySelector(".user-preview");
    const time = row.querySelector(".user-time");
    if (preview) preview.textContent = data.message;
    if (time) time.textContent = data.time;

    const chatPanel = document.querySelector(".chat-panel");
    const activeChat = chatPanel ? chatPanel.dataset.chatWith : null;
    if (activeChat === data.sender) {
        window.chatSocket.emit("mark_chat_read", {
            other_user: data.sender,
            message_id: data.message_id,
        });
        return;
    }

    updateUnreadBadge(data.sender, Number(row.dataset.unreadCount || 0) + 1);
});

window.chatSocket.on("conversation_read", (data) => {
    updateUnreadBadge(data.contact_username, 0);
});
