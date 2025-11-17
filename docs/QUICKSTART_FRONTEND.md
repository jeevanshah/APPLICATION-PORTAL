# Quick Start Guide - Frontend Development

Get up and running with the Application Portal API in 5 minutes!

## Prerequisites

- Node.js 16+ installed
- Backend server running on `http://localhost:8000`
- Basic knowledge of React/TypeScript

---

## Step 1: Setup Your Project

```bash
# Create a new React + TypeScript project
npm create vite@latest my-app -- --template react-ts
cd my-app
npm install

# Install dependencies
npm install axios
npm install -D @types/node
```

---

## Step 2: Create API Client

Create `src/api/client.ts`:

```typescript
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token expiration
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(username: string, password: string) {
    const response = await this.client.post('/auth/login', { username, password });
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  }

  // Applications
  async createApplication(data: { student_profile_id: string; course_offering_id: string }) {
    const response = await this.client.post('/applications', data);
    return response.data;
  }

  async getApplication(id: string) {
    const response = await this.client.get(`/applications/${id}`);
    return response.data;
  }

  // Step updates
  async updateStep(applicationId: string, stepNumber: number, stepName: string, data: any) {
    const response = await this.client.patch(
      `/applications/${applicationId}/steps/${stepNumber}/${stepName}`,
      data
    );
    return response.data;
  }
}

export const api = new APIClient();
```

---

## Step 3: Test the Connection

Create `src/App.tsx`:

```typescript
import { useEffect, useState } from 'react';
import { api } from './api/client';

function App() {
  const [user, setUser] = useState(null);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    try {
      const result = await api.login('test.agent@agency.com', 'AgentPass123!');
      setUser(result.user);
      console.log('Logged in successfully!', result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Application Portal - Quick Start</h1>
      
      {!user ? (
        <div>
          <button onClick={handleLogin}>
            Login as Test Agent
          </button>
          {error && <p style={{ color: 'red' }}>{error}</p>}
        </div>
      ) : (
        <div>
          <h2>Welcome, {user.email}!</h2>
          <p>Role: {user.role}</p>
          <p>Status: {user.status}</p>
        </div>
      )}
    </div>
  );
}

export default App;
```

---

## Step 4: Run Your App

```bash
npm run dev
```

Open http://localhost:5173 and click "Login as Test Agent". You should see the user details!

---

## Step 5: Create Your First Application

Add this to `App.tsx`:

```typescript
const [applicationId, setApplicationId] = useState('');

const handleCreateApp = async () => {
  try {
    // Replace with actual UUIDs from your database
    const result = await api.createApplication({
      student_profile_id: 'your-student-uuid',
      course_offering_id: 'your-course-uuid',
    });
    setApplicationId(result.application.id);
    console.log('Application created!', result);
  } catch (err: any) {
    console.error('Failed to create application:', err.response?.data);
  }
};

// Add button to UI
<button onClick={handleCreateApp}>Create Application</button>
```

---

## Step 6: Update a Step

```typescript
const handleUpdateStep1 = async () => {
  try {
    const result = await api.updateStep(
      applicationId,
      1,
      'personal-details',
      {
        given_name: 'John',
        family_name: 'Smith',
        date_of_birth: '2000-01-15',
        gender: 'Male',
        email: 'john@example.com',
        phone: '+61412345678',
        street_address: '123 Main St',
        suburb: 'Sydney',
        state: 'NSW',
        postcode: '2000',
        country: 'Australia',
        passport_number: 'N1234567',
        nationality: 'Australian',
        country_of_birth: 'Australia',
      }
    );
    
    console.log('Step 1 saved!', result);
    console.log('Progress:', result.completion_percentage + '%');
    console.log('Next step:', result.next_step);
  } catch (err: any) {
    console.error('Failed to update step:', err.response?.data);
  }
};

// Add button
<button onClick={handleUpdateStep1}>Save Personal Details</button>
```

---

## Common Patterns

### 1. Form with Auto-Save

```typescript
import { useEffect, useState } from 'react';
import { debounce } from 'lodash';

function PersonalDetailsForm({ applicationId }: { applicationId: string }) {
  const [formData, setFormData] = useState({
    given_name: '',
    family_name: '',
    // ... other fields
  });

  // Auto-save 2 seconds after user stops typing
  useEffect(() => {
    const saveData = debounce(async () => {
      if (formData.given_name) {
        await api.updateStep(applicationId, 1, 'personal-details', formData);
        console.log('Auto-saved!');
      }
    }, 2000);

    saveData();
    return () => saveData.cancel();
  }, [formData, applicationId]);

  return (
    <form>
      <input
        value={formData.given_name}
        onChange={(e) => setFormData({ ...formData, given_name: e.target.value })}
        placeholder="Given Name"
      />
      {/* ... other fields */}
    </form>
  );
}
```

### 2. Progress Indicator

```typescript
function ProgressIndicator({ percentage, nextStep }: { percentage: number; nextStep: string | null }) {
  return (
    <div>
      <div style={{ 
        width: '100%', 
        backgroundColor: '#e0e0e0', 
        borderRadius: '4px',
        height: '24px'
      }}>
        <div style={{ 
          width: `${percentage}%`, 
          backgroundColor: '#4caf50', 
          height: '100%',
          borderRadius: '4px',
          transition: 'width 0.3s ease'
        }}>
          <span style={{ padding: '0 8px', color: 'white' }}>
            {percentage}% Complete
          </span>
        </div>
      </div>
      {nextStep && <p>Next: {formatStepName(nextStep)}</p>}
    </div>
  );
}

function formatStepName(step: string): string {
  return step
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
```

### 3. Error Handling

```typescript
function handleError(error: any) {
  if (error.response) {
    const { status, data } = error.response;
    
    switch (status) {
      case 401:
        return 'Please log in to continue';
      case 403:
        return 'You do not have permission to perform this action';
      case 422:
        if (Array.isArray(data.detail)) {
          // Pydantic validation errors
          return data.detail.map((err: any) => 
            `${err.loc.join('.')}: ${err.msg}`
          ).join(', ');
        }
        return data.detail; // Simple string error
      case 404:
        return 'Application not found';
      default:
        return 'An error occurred. Please try again.';
    }
  }
  return 'Network error. Please check your connection.';
}
```

---

## Environment Variables

Create `.env`:

```bash
VITE_API_URL=http://localhost:8000/api/v1
```

Create `.env.production`:

```bash
VITE_API_URL=https://api.yourdomain.com/api/v1
```

---

## Testing with Postman

1. Import the collection: `docs/Application_Portal_API.postman_collection.json`
2. Login with the "Login (Agent)" request
3. The token is automatically saved
4. Try other requests!

---

## Next Steps

1. ✅ Read the full [Frontend Integration Guide](./FRONTEND_INTEGRATION.md)
2. ✅ Copy TypeScript types from [api-types.ts](./api-types.ts)
3. ✅ Build your form components for all 12 steps
4. ✅ Implement progress tracking
5. ✅ Add validation and error handling

---

## Troubleshooting

### CORS Errors

If you see CORS errors, make sure the backend has CORS enabled for your origin:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 401 Unauthorized

- Check if token is stored: `console.log(localStorage.getItem('access_token'))`
- Check if token is included in headers
- Token might be expired - login again

### 422 Validation Errors

- Check the error details: `console.log(error.response.data.detail)`
- Verify your data matches the expected format
- Check date formats (YYYY-MM-DD)
- Ensure required fields are included

---

## Useful Resources

- [Full API Documentation](./FRONTEND_INTEGRATION.md)
- [TypeScript Types](./api-types.ts)
- [Postman Collection](./Application_Portal_API.postman_collection.json)
- [Backend Schema Definitions](../backend/app/schemas/)

Happy coding! 🚀
