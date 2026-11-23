# Assets

This folder ships with pre-generated sound effects, BGM and voice lines used by the Windows release.

At runtime, if `assets/audio/` is missing or incomplete, the game synthesizes sound effects and BGM into `saves/audio_cache/`. Voice lines are optional; without `assets/voice/`, the game simply plays no voice.

## Audio layout

```text
assets/
├─ audio/
│  ├─ bgm.wav
│  ├─ sfx_shoot.wav
│  ├─ sfx_shoot2.wav
│  ├─ sfx_hit.wav
│  ├─ sfx_kill.wav
│  ├─ sfx_big.wav
│  ├─ sfx_hurt.wav
│  ├─ sfx_skill.wav
│  ├─ sfx_pick.wav
│  ├─ sfx_card.wav
│  └─ sfx_boss.wav
└─ voice/
   ├─ zh_start.wav
   ├─ zh_death.wav
   └─ ...
```

The voice file naming convention is `<lang>_<key>.wav`, where `lang` is `zh` or `en` and `key` is one of `start`, `layer`, `boss`, `clear`, `death`, `revive`, `shield`.

## Custom audio

You can replace any file with your own recording, TTS output or music. Keep the same filename and format (16-bit PCM WAV is recommended). Only add audio you have the right to distribute; the repository's Apache-2.0 license does not automatically cover third-party voice packs or music.
