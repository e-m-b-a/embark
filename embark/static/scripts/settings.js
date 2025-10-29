document.getElementById("orchestrator-toggle").addEventListener("change", async (e) => {
    "use strict";
    try {
    const response = await fetch("toggle-orchestrator/", {
        method: "GET",
        credentials: "same-origin",
    });
    if (!response.ok) {
        const data = await response.json();
        console.error("Failed to save orchestrator setting:", data.message);
    }
    } catch (error) {
    console.error("Error saving orchestrator setting:", error);
    }
});
