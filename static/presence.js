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
