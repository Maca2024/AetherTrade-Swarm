'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'
import { LogIn, LogOut, User as UserIcon, Chrome } from 'lucide-react'

export default function AuthButton() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const supabase = createClient()

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      setLoading(false)
    }
    getUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleGoogleLogin = async () => {
    setLoading(true)
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
      },
    })
  }

  const handleLogout = async () => {
    setLoading(true)
    await supabase.auth.signOut()
    setUser(null)
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="h-9 w-24 rounded-lg bg-white/5 animate-pulse" />
    )
  }

  if (user) {
    return (
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          {user.user_metadata?.avatar_url ? (
            <img
              src={user.user_metadata.avatar_url}
              alt=""
              className="w-7 h-7 rounded-full border border-white/20"
            />
          ) : (
            <UserIcon className="w-5 h-5 text-white/50" />
          )}
          <span className="text-xs text-white/50 hidden sm:inline">
            {user.user_metadata?.full_name || user.email?.split('@')[0]}
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/40 hover:text-white/60 transition-colors"
          style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <LogOut className="w-3.5 h-3.5" />
          Uitloggen
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={handleGoogleLogin}
      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white hover:opacity-90 transition-opacity"
      style={{
        background: 'linear-gradient(135deg, rgba(124,58,237,0.3), rgba(0,212,255,0.2))',
        border: '1px solid rgba(124,58,237,0.4)',
      }}
    >
      <Chrome className="w-4 h-4" />
      Inloggen met Google
    </button>
  )
}
