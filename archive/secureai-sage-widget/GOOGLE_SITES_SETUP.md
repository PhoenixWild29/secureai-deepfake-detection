# Embedding SecureSage in Google Sites

Since your website is hosted on Google Sites, you'll need to use an iframe embed. Here's how to do it:

## Step 1: Deploy the Embed Page

First, copy the `embed.html` file to your Guardian server so it's accessible via URL:

```bash
# On your DigitalOcean server
cd ~/secureai-deepfake-detection
docker cp secureai-sage-widget/embed.html secureai-nginx:/usr/share/nginx/html/
```

This will make it accessible at: `https://guardian.secureai.dev/embed.html`

## Step 2: Embed in Google Sites

1. **Open your Google Sites editor** (sites.google.com)

2. **Go to the page** where you want SecureSage to appear (where the current OpenAI link is)

3. **Click "Insert"** in the right sidebar

4. **Select "Embed"** from the insert options

5. **Choose "Embed code"** tab

6. **Paste this iframe code:**

```html
<iframe 
    src="https://guardian.secureai.dev/embed.html" 
    width="100%" 
    height="600" 
    frameborder="0" 
    style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);"
    allow="clipboard-read; clipboard-write">
</iframe>
```

7. **Click "Insert"**

8. **Adjust the size** by dragging the corners of the embedded iframe

9. **Publish your site**

## Alternative: Custom Size

If you want a specific size, you can adjust the width and height:

```html
<iframe 
    src="https://guardian.secureai.dev/embed.html" 
    width="450" 
    height="650" 
    frameborder="0" 
    style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);"
    allow="clipboard-read; clipboard-write">
</iframe>
```

## Step 3: Replace the Current Link

1. **Remove or replace** the current text/link that says:
   - "Click on the below link to engage with SecureSage..."
   - The link: "chat.openai.com/g/g-oAxwNWIlu-securesage"

2. **Add a heading** like "Chat with SecureSage" above the embedded iframe

3. **Optionally add description text** like:
   - "Ask SecureSage questions about cybersecurity, SecureAI services, and our platform."

## Mobile Responsive

The embed will automatically adjust to mobile devices. If you want to ensure it looks good on mobile, you can use responsive sizing:

```html
<div style="position: relative; padding-bottom: 120%; height: 0; overflow: hidden;">
    <iframe 
        src="https://guardian.secureai.dev/embed.html" 
        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
        allow="clipboard-read; clipboard-write">
    </iframe>
</div>
```

## Troubleshooting

**If the iframe doesn't load:**
- Check that `https://guardian.secureai.dev/embed.html` is accessible in your browser
- Verify CORS headers are set correctly (should work since it's an iframe)
- Make sure the file was copied to the Nginx container

**If you see CORS errors:**
- The embed.html file needs to be served from the same domain or with proper CORS headers
- Check Nginx configuration allows iframe embedding

**If SecureSage shows "offline":**
- Verify the backend API is running: `https://guardian.secureai.dev/api/sage/chat`
- Check that GEMINI_API_KEY is set on the backend
- Check browser console for specific error messages

## Testing

1. **Test the embed URL directly**: Open `https://guardian.secureai.dev/embed.html` in a browser
2. **Test in Google Sites preview**: Use the preview feature before publishing
3. **Test on mobile**: Check how it looks on mobile devices

## Next Steps

After embedding:
1. Remove the old OpenAI link
2. Update the text around SecureSage to explain what it is
3. Test the chat functionality
4. Publish your site

The embedded SecureSage will use the same backend API as Guardian, so it has access to all your training data and documentation!
