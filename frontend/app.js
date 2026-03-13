/**
 * EPRA Fuel Prices Tracker - Application Logic
 * Architecture: Serverless Part 2 (Cognito Auth, DynamoDB Data, S3 Uploads)
 */

// ==========================================
// CONFIGURATION (Update these with AWS deployed values)
// ==========================================
const CONFIG = {
    // API Gateway Endpoints
    apiBaseUrl: 'https://your-api-gateway-id.execute-api.region.amazonaws.com/prod',
    
    // Auth Token keys (for local storage handling)
    tokenKey: 'epra_id_token'
};

// ==========================================
// STATE MANAGEMENT & DOM ELEMENTS
// ==========================================
let currentState = {
    isAuthenticated: false,
    userRole: null, // "RegularUsers" or "Admins"
    token: null,
    username: null
};

// DOM Elements - Auth & Nav
const loginBtn = document.getElementById('loginBtn');
const logoutBtn = document.getElementById('logoutBtn');
const heroLoginBtn = document.getElementById('heroLoginBtn');
const userInfoEl = document.getElementById('userInfo');
const roleBadgeEl = document.getElementById('roleBadge');
const usernameEl = document.getElementById('usernameDisplay');

// DOM Elements - Sections
const welcomeSection = document.getElementById('welcomeSection');
const dashboardSection = document.getElementById('dashboardSection');
const adminPanel = document.getElementById('adminPanel');

// DOM Elements - Admin Panel
const epraPdfFile = document.getElementById('epraPdfFile');
const fileNameDisplay = document.getElementById('fileName');
const uploadTriggerBtn = document.getElementById('uploadTriggerBtn');
const uploadStatus = document.getElementById('uploadStatus');

// DOM Elements - Prices Table
const pricesTableBody = document.getElementById('pricesTableBody');
const tableLoader = document.getElementById('tableLoader');
const tableError = document.getElementById('tableError');
const refreshBtn = document.getElementById('refreshBtn');

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    checkAuthState();
    setupEventListeners();
});

// ==========================================
// AUTHENTICATION FLOW
// ==========================================
function checkAuthState() {
    // In a real app, you would parse the URL fragment for token (Implicit Grant)
    // OR check localStorage/sessionStorage for saved token
    // OR integrate AWS Amplify / Amazon Cognito Hosted UI sdk

    const storedToken = localStorage.getItem(CONFIG.tokenKey);
    if (storedToken) {
        // Mock parsing JWT payload here.
        handleLoginSuccess(JSON.parse(storedToken));
    } else {
        showUnauthenticatedView();
    }
}

// NOTE: This login is mocked to demonstrate the two workflows.
// Replace this with standard Cognito Hosted UI redirection:
// window.location.href = `https://<YOUR_DOMAIN>.auth.<REGION>.amazoncognito.com/login?...`
function triggerLoginFlow() {
    const roleChoice = confirm("MOCK LOGIN:\nClick 'OK' to login as Admin (Write Data)\nClick 'Cancel' to login as Regular User (Read-Only)");
    
    // Simulate JWT payload structure
    const mockTokenPayload = {
        sub: "1234567890",
        "cognito:username": roleChoice ? "AdminUser1" : "Citizen007",
        "cognito:groups": roleChoice ? ["Admins"] : ["RegularUsers"],
        // A real JWT is encoded. We store this raw JSON object locally for mock purposes.
        "raw_jwt": "eyMockHeader.eyMockPayload.MockSignature" 
    };

    localStorage.setItem(CONFIG.tokenKey, JSON.stringify(mockTokenPayload));
    handleLoginSuccess(mockTokenPayload);
}

function handleLoginSuccess(tokenPayload) {
    currentState.isAuthenticated = true;
    currentState.token = tokenPayload.raw_jwt; // The token string to pass to API Gateway
    currentState.username = tokenPayload["cognito:username"];
    currentState.userRole = tokenPayload["cognito:groups"][0]; // Extracted from token group array

    updateUINavState();
    showDashboardView();
    
    // Automatically fetch prices data upon login
    fetchPricesData();
}

function handleLogout() {
    localStorage.removeItem(CONFIG.tokenKey);
    currentState = {
        isAuthenticated: false,
        userRole: null,
        token: null,
        username: null
    };
    
    updateUINavState();
    showUnauthenticatedView();
}

// ==========================================
// UI STATE TOGGLES
// ==========================================
function updateUINavState() {
    if (currentState.isAuthenticated) {
        loginBtn.classList.add('hidden');
        logoutBtn.classList.remove('hidden');
        userInfoEl.classList.remove('hidden');
        
        usernameEl.textContent = currentState.username;
        roleBadgeEl.textContent = currentState.userRole === "Admins" ? "Admin" : "User";
        
        if (currentState.userRole === "Admins") {
            roleBadgeEl.classList.add('admin');
        } else {
            roleBadgeEl.classList.remove('admin');
        }
    } else {
        loginBtn.classList.remove('hidden');
        logoutBtn.classList.add('hidden');
        userInfoEl.classList.add('hidden');
    }
}

function showUnauthenticatedView() {
    welcomeSection.classList.remove('hidden');
    welcomeSection.style.display = "flex";
    
    dashboardSection.classList.add('hidden');
}

function showDashboardView() {
    welcomeSection.classList.add('hidden');
    welcomeSection.style.display = "none";
    
    dashboardSection.classList.remove('hidden');

    // Role-based visibility: Show admin panel ONLY if user belongs to "Admins" group
    if (currentState.userRole === "Admins") {
        adminPanel.classList.remove('hidden');
    } else {
        adminPanel.classList.add('hidden');
    }
}

// ==========================================
// API INTERACTIONS (API GATEWAY)
// ==========================================

/**
 * Valid for BOTH Admins and RegularUsers
 * Step 3: Hits GET /prices with token
 */
async function fetchPricesData() {
    tableLoader.classList.remove('hidden');
    tableError.classList.add('hidden');
    pricesTableBody.innerHTML = '';

    try {
        /*
        // REAL API CALL TO API GATEWAY
        const response = await fetch(`${CONFIG.apiBaseUrl}/prices`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${currentState.token}` }
        });
        
        if (!response.ok) throw new Error("Failed to fetch data");
        const data = await response.json();
        */

        // MOCK API DELAY & RESPONSE
        await new Promise(resolve => setTimeout(resolve, 1500));
        const mockData = [
            { county: "Nairobi", super_petrol: 199.15, diesel: 190.51, kerosene: 188.74, last_updated: "2024-03-14" },
            { county: "Mombasa", super_petrol: 196.21, diesel: 187.57, kerosene: 185.79, last_updated: "2024-03-14" },
            { county: "Nakuru", super_petrol: 198.30, diesel: 190.01, kerosene: 188.24, last_updated: "2024-03-14" },
            { county: "Eldoret", super_petrol: 199.98, diesel: 191.68, kerosene: 189.91, last_updated: "2024-03-14" }
        ];
        
        populatePricesTable(mockData);

    } catch (error) {
        console.error("API Fetch Error:", error);
        tableError.classList.remove('hidden');
    } finally {
        tableLoader.classList.add('hidden');
    }
}

/**
 * Valid ONLY for Admins
 * Step 2: Request signed URL from API Gateway
 * Step 5: Upload directly to S3
 */
async function uploadAdminDocument() {
    const file = epraPdfFile.files[0];
    if (!file) return;

    uploadTriggerBtn.disabled = true;
    uploadTriggerBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    hideStatus();

    try {
        // Step 1: Get Pre-Signed URL from GatekeeperLambda
        /*
        // REAL CALL
        const uploadUrlResponse = await fetch(`${CONFIG.apiBaseUrl}/request-upload?filename=${file.name}&contentType=${file.type}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${currentState.token}` } // API Gateway verifies Cognito Group here
        });

        if (uploadUrlResponse.status === 403) throw new Error("Forbidden: You are not authorized.");
        if (!uploadUrlResponse.ok) throw new Error("Failed to generate secure link");
        
        const { uploadUrl } = await uploadUrlResponse.json();

        // Step 2: PUT file directly to S3
        const s3UploadResponse = await fetch(uploadUrl, {
            method: 'PUT',
            body: file,
            headers: {
                'Content-Type': file.type
            }
        });

        if (!s3UploadResponse.ok) throw new Error("S3 Upload Failed");
        */

        // MOCK PROGRESS
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        if (currentState.userRole !== "Admins") {
            throw new Error("Forbidden: Only Admins can execute this action.");
        }

        showStatus("success", `Successfully uploaded "${file.name}". S3 pipeline triggered! Checking for database updates...`);
        
        // Reset File Input
        epraPdfFile.value = '';
        fileNameDisplay.textContent = "Select PDF Document...";
        
        // Auto-refresh prices after 3 seconds (Simulate Textract Processing time)
        setTimeout(() => {
            fetchPricesData();
            showStatus("success", "Database updated. New prices loaded.");
        }, 3000);

    } catch (error) {
        console.error("Upload Error:", error);
        showStatus("error", error.message || "Failed to upload document. Please try again.");
    } finally {
        uploadTriggerBtn.disabled = false;
        uploadTriggerBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Upload & Process';
    }
}

// ==========================================
// DOM RENDERERS & EVENT LISTENERS
// ==========================================
function populatePricesTable(data) {
    pricesTableBody.innerHTML = '';
    
    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${row.county}</strong></td>
            <td>KSh ${row.super_petrol.toFixed(2)}</td>
            <td>KSh ${row.diesel.toFixed(2)}</td>
            <td>KSh ${row.kerosene.toFixed(2)}</td>
            <td style="color: var(--text-muted); font-size: 0.85em;">${row.last_updated}</td>
        `;
        pricesTableBody.appendChild(tr);
    });
}

function setupEventListeners() {
    loginBtn.addEventListener('click', triggerLoginFlow);
    heroLoginBtn.addEventListener('click', triggerLoginFlow);
    logoutBtn.addEventListener('click', handleLogout);
    refreshBtn.addEventListener('click', fetchPricesData);
    
    // Admin File Selection Label Update
    epraPdfFile.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileNameDisplay.textContent = e.target.files[0].name;
            uploadTriggerBtn.disabled = false;
        } else {
            fileNameDisplay.textContent = "Select PDF Document...";
            uploadTriggerBtn.disabled = true;
        }
    });

    uploadTriggerBtn.addEventListener('click', uploadAdminDocument);
}

function showStatus(type, message) {
    uploadStatus.className = 'status-message';
    uploadStatus.classList.add(type === 'success' ? 'status-success' : 'status-error');
    uploadStatus.innerHTML = type === 'success' 
        ? `<i class="fa-solid fa-check-circle"></i> ${message}`
        : `<i class="fa-solid fa-triangle-exclamation"></i> ${message}`;
}
function hideStatus() {
    uploadStatus.className = 'status-message';
}
