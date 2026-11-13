import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

const API_URL = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');

export default function App() {
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = setTimeout(() => controller.abort(), 15000);

    async function loadHello() {
      setError('');
      setMessage('');
      try {
        if (!API_URL) {
          throw new Error('Hãy đặt EXPO_PUBLIC_API_URL trong Frontend/.env.');
        }
        const response = await fetch(`${API_URL}/`, { signal: controller.signal });
        if (!response.ok) throw new Error(`Backend trả về lỗi ${response.status}.`);
        const data = await response.json();
        if (typeof data.message !== 'string' || !data.message.trim()) {
          throw new Error('Backend chưa trả về message hợp lệ.');
        }
        if (active) setMessage(data.message);
      } catch (err) {
        if (active) {
          setError(err.name === 'AbortError'
            ? 'Kết nối quá hạn. Hãy thử lại.'
            : (err.message || 'Không kết nối được backend.'));
        }
      } finally {
        clearTimeout(timeout);
      }
    }

    loadHello();
    return () => {
      active = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [attempt]);

  return (
    <View style={styles.container}>
      {message ? <Text style={styles.message}>{message}</Text> : error ? (
        <View style={styles.error}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable accessibilityRole="button" onPress={() => setAttempt(value => value + 1)}>
            <Text style={styles.retry}>Thử lại</Text>
          </Pressable>
        </View>
      ) : <ActivityIndicator size="large" color="#222222" />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, backgroundColor: '#ffffff' },
  message: { fontSize: 32, color: '#222222' },
  error: { alignItems: 'center', gap: 20 },
  errorText: { fontSize: 16, textAlign: 'center', color: '#b42318' },
  retry: { fontSize: 18, color: '#175cd3', padding: 12 },
});
