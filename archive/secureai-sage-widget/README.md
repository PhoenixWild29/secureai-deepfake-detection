# SecureSage Embeddable Widget

Embed SecureSage AI consultant on your website (www.secureai.dev) with a simple script tag.

## Quick Start

### Option 1: Simple Embed (Recommended)

Add this to your website's HTML where you want SecureSage to appear:

```html
<!-- Add this before closing </body> tag -->
<div id="secureai-sage-widget"></div>
<script src="https://guardian.secureai.dev/secureai-sage-widget.js"></script>
```

That's it! SecureSage will appear as a floating widget in the bottom-right corner.

### Option 2: Custom Configuration

```html
<div id="secureai-sage-widget"></div>
<script src="https://guardian.secureai.dev/secureai-sage-widget.js"></script>
<script>
  // Initialize with custom options
  window.secureaiSage = new SecureSageWidget('secureai-sage-widget', {
    apiUrl: 'https://guardian.secureai.dev',
    theme: 'dark',
    position: 'bottom-right', // or 'bottom-left', 'top-right', 'top-left'
    width: '400px',
    height: '600px'
  });
</script>
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `apiUrl` | `https://guardian.secureai.dev` | Backend API URL |
| `theme` | `dark` | Widget theme (currently only 'dark') |
| `position` | `bottom-right` | Widget position on page |
| `width` | `400px` | Widget width |
| `height` | `600px` | Widget height |

## Deployment

### Step 1: Copy the widget file to your server

Copy `secureai-sage-widget.js` to your Nginx static files directory:

```bash
# On your server
cp secureai-sage-widget/secureai-sage-widget.js /path/to/nginx/html/
```

Or if using the Guardian server:

```bash
# Copy to Guardian Nginx container
docker cp secureai-sage-widget/secureai-sage-widget.js secureai-nginx:/usr/share/nginx/html/
```

### Step 2: Update Nginx config (if needed)

Make sure Nginx serves the widget file with correct CORS headers:

```nginx
location /secureai-sage-widget.js {
    add_header Access-Control-Allow-Origin *;
    add_header Content-Type application/javascript;
}
```

### Step 3: Add to your website

Add the embed code to your www.secureai.dev website HTML.

## Features

✅ **Embeddable** - Works on any website  
✅ **No Dependencies** - Pure vanilla JavaScript  
✅ **Responsive** - Works on desktop and mobile  
✅ **Same Backend** - Uses the same SecureSage API as Guardian  
✅ **Customizable** - Easy to configure position and size  
✅ **Auto-initializes** - Just add the script tag  

## API Endpoint

The widget calls: `https://guardian.secureai.dev/api/sage/chat`

This is the same endpoint used by the Guardian app, so SecureSage will have access to all your training data and documentation.

## Troubleshooting

**Widget not appearing?**
- Check browser console for errors
- Verify the script URL is accessible
- Make sure the container div exists

**API errors?**
- Verify `guardian.secureai.dev/api/sage/chat` is accessible
- Check CORS headers if calling from different domain
- Verify GEMINI_API_KEY is set on backend

**Styling issues?**
- Widget uses fixed positioning - may conflict with other CSS
- Check z-index if widget is behind other elements

## Support

For issues or questions, check the Guardian app logs or contact the development team.
