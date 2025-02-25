from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pyppeteer import launch
from markdownify import markdownify
from pydantic import BaseModel, HttpUrl
from typing import Optional
import asyncio

app = FastAPI(
    title="HTML to Markdown Converter",
    description="API to convert webpage HTML content to Markdown format using Puppeteer"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def fetch_webpage_content(url: str) -> Optional[str]:
    """Fetch webpage content using Puppeteer"""
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    )
    try:
        page = await browser.newPage()
        
        # Set viewport and user agent
        await page.setViewport({'width': 1920, 'height': 1080})
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Set extra headers
        await page.setExtraHTTPHeaders({
            'Referer': 'https://google.com',
            'Accept-Language': 'en-US,en;q=0.9'
        })

        # Navigate to page with timeout
        await page.goto(url, {'waitUntil': 'networkidle0', 'timeout': 60000})
        
        # Improved scroll and lazy loading handling
        await page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let lastHeight = 0;
                let retries = 0;
                const maxRetries = 5;
                
                const timer = setInterval(async () => {
                    const currentHeight = document.documentElement.scrollHeight;
                    window.scrollTo(0, currentHeight);
                    
                    // Wait for any lazy-loaded content
                    await new Promise(r => setTimeout(r, 1000));
                    
                    if (currentHeight === lastHeight) {
                        retries++;
                        if (retries >= maxRetries) {
                            clearInterval(timer);
                            resolve();
                        }
                    } else {
                        retries = 0;
                    }
                    
                    lastHeight = currentHeight;
                }, 1000);
            });
        }
        """)
        
        # Wait for dynamic content
        await page.waitFor(2000)
        
        # Get the final HTML content
        html_content = await page.content()
        return html_content
        
    except Exception as e:
        print(f"Browser error details: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    finally:
        await browser.close()

@app.get("/convert")
async def convert_to_markdown(url: HttpUrl):
    """Convert webpage HTML to Markdown"""
    try:
        html_content = await fetch_webpage_content(str(url))
        markdown_content = markdownify(html_content, heading_style='ATX')
        
        return {
            "url": url,
            "markdown": markdown_content
        }
    except Exception as e:
        print(f"Error details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
        

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)