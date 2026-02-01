# Mobile App Implementation Guide - Step by Step

## 🚀 Quick Start Guide

This guide provides step-by-step instructions to build Android and iOS apps for Winu.app.

---

## 📋 Prerequisites Checklist

### **Required Accounts**
- [ ] Apple Developer Account ($99/year) - for iOS
- [ ] Google Play Developer Account ($25 one-time) - for Android
- [ ] Firebase Account (free) - for push notifications

### **Development Tools**
- [ ] Node.js 18+ installed
- [ ] React Native CLI or Expo CLI
- [ ] Xcode (macOS only, for iOS)
- [ ] Android Studio (for Android)
- [ ] Code editor (VS Code recommended)

---

## 🛠️ Step 1: Choose Your Framework

### **Recommendation: React Native with Expo**

**Why Expo?**
- Faster development
- Built-in push notifications
- Easy deployment
- Over-the-air updates
- No need for native code initially

**Installation:**
```bash
npm install -g expo-cli
npx create-expo-app winu-mobile --template
cd winu-mobile
```

---

## 📱 Step 2: Project Setup

### **2.1 Initialize React Native Project**

```bash
# Using Expo (Recommended)
npx create-expo-app winu-mobile --template blank-typescript
cd winu-mobile

# Or using React Native CLI
npx react-native init WinuMobile --template react-native-template-typescript
```

### **2.2 Install Dependencies**

```bash
npm install @react-navigation/native @react-navigation/stack @react-navigation/bottom-tabs
npm install react-native-screens react-native-safe-area-context
npm install @tanstack/react-query axios
npm install @react-native-async-storage/async-storage
npm install expo-secure-store
npm install react-native-push-notification
npm install socket.io-client
npm install react-native-gesture-handler
npm install react-native-reanimated
```

### **2.3 Project Structure**

```
winu-mobile/
├── src/
│   ├── api/
│   │   ├── client.ts
│   │   ├── endpoints.ts
│   │   └── types.ts
│   ├── components/
│   │   ├── SignalCard.tsx
│   │   ├── LoadingSpinner.tsx
│   │   └── ErrorMessage.tsx
│   ├── screens/
│   │   ├── LoginScreen.tsx
│   │   ├── DashboardScreen.tsx
│   │   ├── SignalsScreen.tsx
│   │   └── SettingsScreen.tsx
│   ├── navigation/
│   │   └── AppNavigator.tsx
│   ├── store/
│   │   └── authStore.ts
│   ├── hooks/
│   │   └── useAuth.ts
│   └── utils/
│       └── storage.ts
├── app.json
├── package.json
└── tsconfig.json
```

---

## 🔌 Step 3: API Integration

### **3.1 Create API Client**

Create `src/api/client.ts`:

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios';
import * as SecureStore from 'expo-secure-store';

const API_BASE_URL = 'https://api.winu.app';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add token to requests
    this.client.interceptors.request.use(async (config) => {
      const token = await SecureStore.getItemAsync('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token expiry
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired, logout user
          await SecureStore.deleteItemAsync('auth_token');
          // Navigate to login (handle in app)
        }
        return Promise.reject(error);
      }
    );
  }

  async login(username: string, password: string) {
    const response = await this.client.post('/auth/login', {
      username,
      password,
    });
    
    const { access_token } = response.data;
    await SecureStore.setItemAsync('auth_token', access_token);
    return response.data;
  }

  async getSignals(params?: {
    symbol?: string;
    timeframe?: string;
    direction?: string;
    limit?: number;
  }) {
    const response = await this.client.get('/signals/recent', { params });
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  async getAccountBalance(accountId: number) {
    const response = await this.client.get(
      `/api/bot/multi-account/accounts/${accountId}/balance`
    );
    return response.data;
  }

  async getDashboardStats() {
    const response = await this.client.get('/api/bot/multi-account/dashboard');
    return response.data;
  }

  async logout() {
    await SecureStore.deleteItemAsync('auth_token');
  }
}

export const apiClient = new APIClient();
```

### **3.2 Create API Types**

Create `src/api/types.ts`:

```typescript
export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  subscription_status: string;
  current_period_end?: string;
}

export interface Signal {
  id: number;
  symbol: string;
  timeframe: string;
  direction: 'LONG' | 'SHORT';
  score: number;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2?: number;
  take_profit_3?: number;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user?: User;
}

export interface DashboardStats {
  total_balance: number;
  total_pnl: number;
  total_trades: number;
  win_rate: number;
  active_positions: number;
}
```

---

## 🔐 Step 4: Authentication Implementation

### **4.1 Create Auth Store**

Create `src/store/authStore.ts`:

```typescript
import { create } from 'zustand';
import { apiClient } from '../api/client';
import * as SecureStore from 'expo-secure-store';
import type { User, LoginResponse } from '../api/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (username: string, password: string) => {
    try {
      const response: LoginResponse = await apiClient.login(username, password);
      const user = await apiClient.getCurrentUser();
      
      set({
        user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    await apiClient.logout();
    set({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  },

  checkAuth: async () => {
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      if (token) {
        const user = await apiClient.getCurrentUser();
        set({
          user,
          token,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      await SecureStore.deleteItemAsync('auth_token');
      set({ isLoading: false });
    }
  },
}));
```

### **4.2 Create Login Screen**

Create `src/screens/LoginScreen.tsx`:

```typescript
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useAuthStore } from '../store/authStore';

export default function LoginScreen({ navigation }: any) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuthStore();

  const handleLogin = async () => {
    if (!username || !password) {
      Alert.alert('Error', 'Please enter username and password');
      return;
    }

    setLoading(true);
    try {
      await login(username, password);
      // Navigation handled by AppNavigator based on auth state
    } catch (error: any) {
      Alert.alert('Login Failed', error.response?.data?.detail || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Winu Bot Signal</Text>
      <Text style={styles.subtitle}>AI-Powered Trading Signals</Text>

      <TextInput
        style={styles.input}
        placeholder="Username"
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
      />

      <TextInput
        style={styles.input}
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />

      <TouchableOpacity
        style={styles.button}
        onPress={handleLogin}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Login</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.linkButton}
        onPress={() => navigation.navigate('Register')}
      >
        <Text style={styles.linkText}>Don't have an account? Register</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: '#1a1a2e',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 16,
    color: '#888',
    textAlign: 'center',
    marginBottom: 40,
  },
  input: {
    backgroundColor: '#2a2a3e',
    borderRadius: 8,
    padding: 15,
    marginBottom: 15,
    color: '#fff',
    fontSize: 16,
  },
  button: {
    backgroundColor: '#667eea',
    borderRadius: 8,
    padding: 15,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  linkButton: {
    marginTop: 20,
    alignItems: 'center',
  },
  linkText: {
    color: '#667eea',
    fontSize: 14,
  },
});
```

---

## 📊 Step 5: Signals Screen Implementation

### **5.1 Create Signals Screen**

Create `src/screens/SignalsScreen.tsx`:

```typescript
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Signal } from '../api/types';
import SignalCard from '../components/SignalCard';

export default function SignalsScreen({ navigation }: any) {
  const [refreshing, setRefreshing] = useState(false);

  const { data: signals, isLoading, refetch } = useQuery({
    queryKey: ['signals'],
    queryFn: () => apiClient.getSignals({ limit: 50 }),
  });

  const onRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text style={styles.loadingText}>Loading signals...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={signals || []}
        renderItem={({ item }: { item: Signal }) => (
          <SignalCard signal={item} onPress={() => navigation.navigate('SignalDetail', { signal: item })} />
        )}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.center}>
            <Text style={styles.emptyText}>No signals available</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#fff',
    fontSize: 16,
  },
  emptyText: {
    color: '#888',
    fontSize: 16,
  },
});
```

### **5.2 Create Signal Card Component**

Create `src/components/SignalCard.tsx`:

```typescript
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import type { Signal } from '../api/types';

interface SignalCardProps {
  signal: Signal;
  onPress: () => void;
}

export default function SignalCard({ signal, onPress }: SignalCardProps) {
  const directionColor = signal.direction === 'LONG' ? '#00ff7f' : '#ff4444';
  const scoreColor = signal.score >= 0.8 ? '#00ff7f' : signal.score >= 0.65 ? '#ffaa00' : '#888';

  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <View style={styles.header}>
        <Text style={styles.symbol}>{signal.symbol}</Text>
        <View style={[styles.directionBadge, { backgroundColor: directionColor }]}>
          <Text style={styles.directionText}>{signal.direction}</Text>
        </View>
      </View>

      <View style={styles.infoRow}>
        <Text style={styles.label}>Score:</Text>
        <Text style={[styles.score, { color: scoreColor }]}>
          {(signal.score * 100).toFixed(0)}%
        </Text>
      </View>

      <View style={styles.infoRow}>
        <Text style={styles.label}>Entry:</Text>
        <Text style={styles.value}>${signal.entry_price.toFixed(2)}</Text>
      </View>

      <View style={styles.infoRow}>
        <Text style={styles.label}>Stop Loss:</Text>
        <Text style={styles.value}>${signal.stop_loss.toFixed(2)}</Text>
      </View>

      <View style={styles.infoRow}>
        <Text style={styles.label}>Take Profit:</Text>
        <Text style={styles.value}>${signal.take_profit_1.toFixed(2)}</Text>
      </View>

      <Text style={styles.timeframe}>{signal.timeframe}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#2a2a3e',
    borderRadius: 12,
    padding: 16,
    margin: 10,
    marginBottom: 0,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  symbol: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  directionBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  directionText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  label: {
    color: '#888',
    fontSize: 14,
  },
  value: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
  score: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  timeframe: {
    color: '#667eea',
    fontSize: 12,
    marginTop: 8,
  },
});
```

---

## 🧭 Step 6: Navigation Setup

### **6.1 Create App Navigator**

Create `src/navigation/AppNavigator.tsx`:

```typescript
import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useAuthStore } from '../store/authStore';

// Screens
import LoginScreen from '../screens/LoginScreen';
import DashboardScreen from '../screens/DashboardScreen';
import SignalsScreen from '../screens/SignalsScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor: '#667eea',
        tabBarInactiveTintColor: '#888',
        tabBarStyle: {
          backgroundColor: '#1a1a2e',
          borderTopColor: '#2a2a3e',
        },
        headerStyle: {
          backgroundColor: '#1a1a2e',
        },
        headerTintColor: '#fff',
      }}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Signals" component={SignalsScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, []);

  if (isLoading) {
    return null; // Show splash screen
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <Stack.Screen name="Main" component={MainTabs} />
        ) : (
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

---

## 🔔 Step 7: Push Notifications Setup

### **7.1 Backend: Add Push Notification Endpoints**

Add to `apps/api/routers/push_notifications.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routers.auth import get_current_active_user
from common.database import User

router = APIRouter(prefix="/api/push", tags=["Push Notifications"])

class DeviceToken(BaseModel):
    device_token: str
    platform: str  # "ios" or "android"

@router.post("/register")
async def register_device_token(
    device: DeviceToken,
    current_user: User = Depends(get_current_active_user)
):
    """Register device token for push notifications."""
    # Store device token in database
    # Associate with user_id
    # Platform-specific handling
    return {"status": "registered"}

@router.post("/unregister")
async def unregister_device_token(
    device_token: str,
    current_user: User = Depends(get_current_active_user)
):
    """Unregister device token."""
    # Remove device token from database
    return {"status": "unregistered"}
```

### **7.2 Mobile: Setup Push Notifications**

Install dependencies:
```bash
npm install expo-notifications
npm install expo-device
```

Create `src/services/pushNotifications.ts`:

```typescript
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import { apiClient } from '../api/client';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export async function registerForPushNotifications() {
  if (!Device.isDevice) {
    console.warn('Must use physical device for Push Notifications');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.warn('Failed to get push token for push notification!');
    return null;
  }

  const token = (await Notifications.getExpoPushTokenAsync()).data;
  
  // Register with backend
  await apiClient.registerDeviceToken(token, Platform.OS);

  return token;
}
```

---

## 🎨 Step 8: UI/UX Design

### **Design Principles**

1. **Dark Theme** (matches web dashboard)
   - Primary: `#1a1a2e`
   - Secondary: `#2a2a3e`
   - Accent: `#667eea`
   - Success: `#00ff7f`
   - Error: `#ff4444`

2. **Typography**
   - Headings: Bold, 20-32px
   - Body: Regular, 14-16px
   - Labels: Medium, 12-14px

3. **Components**
   - Cards with rounded corners (12px)
   - Consistent spacing (8px, 16px, 24px)
   - Clear visual hierarchy

---

## 📦 Step 9: Build & Deploy

### **9.1 Development Build**

```bash
# iOS
npx expo run:ios

# Android
npx expo run:android
```

### **9.2 Production Build**

```bash
# iOS
eas build --platform ios

# Android
eas build --platform android
```

### **9.3 App Store Submission**

**iOS:**
1. Archive build in Xcode
2. Upload to App Store Connect
3. Submit for review

**Android:**
1. Generate signed APK/AAB
2. Upload to Google Play Console
3. Submit for review

---

## ✅ Checklist

### **Backend Tasks**
- [ ] Add mobile app CORS configuration
- [ ] Create push notification endpoints
- [ ] Add token refresh endpoint
- [ ] Test all API endpoints with mobile app

### **Mobile App Tasks**
- [ ] Set up React Native project
- [ ] Implement authentication
- [ ] Create core screens
- [ ] Integrate API
- [ ] Add push notifications
- [ ] Test on devices
- [ ] Submit to app stores

---

## 📚 Additional Resources

- [React Native Documentation](https://reactnative.dev/)
- [Expo Documentation](https://docs.expo.dev/)
- [React Navigation](https://reactnavigation.org/)
- [React Query](https://tanstack.com/query/latest)

---

**Next Steps**: Start with Step 1 and work through each phase systematically.
