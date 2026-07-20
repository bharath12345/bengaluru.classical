/**
 * Cloudflare Email Worker
 * Catches mail to the private submission inbox and forwards raw MIME + attachments
 * to the Django inbound_email endpoint.
 */

export default {
  async email(message, env, ctx) {
    const INBOUND_URL = env.INBOUND_EMAIL_URL;
    const SECRET = env.INBOUND_EMAIL_SECRET;

    const rawMime = await streamToString(message.raw);

    const attachments = [];
    for (const attachment of message.attachments || []) {
      const buffer = await attachment.arrayBuffer();
      const base64 = arrayBufferToBase64(buffer);
      attachments.push({
        name: attachment.name || "attachment.bin",
        content_base64: base64,
        content_type: attachment.contentType || "application/octet-stream",
      });
    }

    const response = await fetch(INBOUND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        secret: SECRET,
        raw_mime: rawMime,
        attachments: attachments,
      }),
    });

    if (!response.ok) {
      console.error("Failed to forward email:", await response.text());
    }
  },
};

async function streamToString(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let result = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    result += decoder.decode(value, { stream: true });
  }
  return result;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
