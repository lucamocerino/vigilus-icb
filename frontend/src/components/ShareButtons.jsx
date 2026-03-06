import { Share2, Twitter, MessageCircle, Send } from 'lucide-react'
import { useState } from 'react'

export default function ShareButtons({ score, level }) {
  const [open, setOpen] = useState(false)

  const text = `🛡️ VIGILUS — Italy Crisis Board — Score: ${score?.toFixed(1) ?? '?'}/100 [${level ?? '?'}]\nDashboard OSINT sicurezza nazionale italiana\n#VIGILUS #OSINT #ItalyCrisisBoard`
  const url = window.location.href

  const channels = [
    { name: 'Twitter/X', icon: Twitter, color: '#1DA1F2',
      href: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}` },
    { name: 'Telegram', icon: Send, color: '#0088cc',
      href: `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}` },
    { name: 'WhatsApp', icon: MessageCircle, color: '#25D366',
      href: `https://wa.me/?text=${encodeURIComponent(text + '\n' + url)}` },
  ]

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-term-surface border border-term-border rounded-lg text-xs text-gray-400 hover:text-white hover:border-indigo-500 transition-colors"
      >
        <Share2 className="w-3 h-3" />
        Condividi
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute bottom-full mb-2 right-0 bg-term-surface border border-term-border rounded-lg shadow-xl z-50 py-1 min-w-[160px]">
            {channels.map(ch => (
              <a
                key={ch.name}
                href={ch.href}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
              >
                <ch.icon className="w-3.5 h-3.5" style={{ color: ch.color }} />
                {ch.name}
              </a>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
