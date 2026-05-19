import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3002';
const APP_DIR = path.join(process.cwd(), 'src/app');

// 1. Encontrar todas las rutas
function getRoutes(dir, baseRoute = '') {
    let routes = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
        if (entry.isDirectory()) {
            // Ignore route groups (folders starting with parentheses like (public))
            let routeSegment = entry.name;
            if (routeSegment.startsWith('(') && routeSegment.endsWith(')')) {
                routes.push(...getRoutes(path.join(dir, entry.name), baseRoute));
            } else {
                routes.push(...getRoutes(path.join(dir, entry.name), `${baseRoute}/${routeSegment}`));
            }
        } else if (entry.isFile() && entry.name === 'page.tsx') {
            let finalRoute = baseRoute === '' ? '/' : baseRoute;
            routes.push(finalRoute);
        }
    }
    return routes;
}

function processDynamicRoutes(routes) {
    return routes.map(route => {
        // Reemplazar [id], [slug], etc. con '1' o 'test'
        return route.replace(/\[([^\]]+)\]/g, (match, param) => {
            if (param === 'id' || param.includes('id')) return '1';
            return 'test';
        });
    });
}

(async () => {
    console.log('Descubriendo rutas...');
    const rawRoutes = getRoutes(APP_DIR);
    const routesToVisit = processDynamicRoutes(rawRoutes);
    // Remover duplicados por si acaso
    const uniqueRoutes = [...new Set(routesToVisit)];
    console.log(`Se encontraron ${uniqueRoutes.length} rutas únicas.`);

    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    let errors = [];

    // Authenticate first
    console.log('Iniciando sesión...');
    try {
        await page.goto(`${BASE_URL}/login`);
        await page.fill('input[type="email"]', 'admin@ccf.org');
        await page.fill('input[type="password"]', 'admin123'); // Assuming standard test credentials
        await page.click('button[type="submit"]');
        await page.waitForTimeout(2000);
        // Set a token directly in localStorage just in case
        await page.evaluate(() => {
            localStorage.setItem('ccf_token', 'fake-admin-token');
        });
    } catch (e) {
        console.log('Login falló, continuando con token simulado...');
        await page.goto(`${BASE_URL}`);
        await page.evaluate(() => {
            localStorage.setItem('ccf_token', 'fake-admin-token');
        });
    }

    // Monitorear errores de consola
    page.on('pageerror', exception => {
        errors.push({ type: 'exception', msg: exception.message });
    });

    page.on('console', msg => {
        if (msg.type() === 'error') {
            errors.push({ type: 'console', msg: msg.text() });
        }
    });

    console.log('Comenzando smoke test...');
    let report = [];

    for (const route of uniqueRoutes) {
        errors = [];
        const url = `${BASE_URL}${route}`;
        try {
            await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
            // Esperar a que React renderice e hidrate
            await page.waitForTimeout(1000);
            
            // Check for Next.js error overlay or React error boundary
            const hasErrorOverlay = await page.evaluate(() => {
                return !!document.querySelector('nextjs-portal') || document.body.innerText.includes('TypeError');
            });

            if (errors.length > 0 || hasErrorOverlay) {
                console.log(`[FAIL] ${route} -> ${errors.length} errores detectados`);
                report.push({
                    route,
                    errors: [...errors],
                    hasOverlay: hasErrorOverlay
                });
            } else {
                console.log(`[OK]   ${route}`);
            }
        } catch (e) {
            console.log(`[ERR]  ${route} -> ${e.message}`);
            report.push({
                route,
                errors: [{ type: 'navigation', msg: e.message }]
            });
        }
    }

    await browser.close();

    fs.writeFileSync('smoke-report.json', JSON.stringify(report, null, 2));
    console.log(`\\nSmoke test completado. ${report.length} rutas con errores. Reporte guardado en smoke-report.json`);
})();
