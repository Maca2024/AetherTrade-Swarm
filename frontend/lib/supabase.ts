import { createBrowserClient } from '@supabase/ssr'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://sooufmgxxuirbsxouxju.supabase.co'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNvb3VmbWd4eHVpcmJzeG91eGp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3NTkxMTQsImV4cCI6MjA5MTMzNTExNH0.Lb0zUHZ3AgLEwHs5BoqrKny2-kQL-Xkz5HGXTquTsO0'

export function createClient() {
  return createBrowserClient(supabaseUrl, supabaseAnonKey)
}
