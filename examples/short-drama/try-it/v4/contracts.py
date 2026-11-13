"""Audio-led production invariants, not a subjective quality certificate."""
def validate_audio_graph(graph,audio_seconds):
    try:
        c=graph['condition'];g=c['inputs'];sample=graph['sample']['inputs'];features=graph['audio_features']['inputs']
        valid=(c['class_type']=='WanSoundImageToVideo' and g['audio_encoder_output']==['audio_features',0]
            and features['audio']==['audio',0] and features['audio_encoder']==['audio_model',0]
            and graph['audio']['class_type']=='LoadAudio' and graph['audio_model']['class_type']=='AudioEncoderLoader'
            and sample['positive']==['condition',0] and sample['negative']==['condition',1] and sample['latent_image']==['condition',2]
            and graph['save']['inputs']['fps']==16 and graph['decode']['inputs']['samples']==['sample',0]
            and graph['save']['inputs']['images']==['decode',0]
            and (g['length']-1)%4==0 and 1<=g['length']<=77 and abs(audio_seconds-g['length']/16)<.002)
    except (KeyError,TypeError):valid=False
    if not valid:raise ValueError('Audio conditioning, locked timebase or frame coverage invalid')

def validate_actor_sources(cuts):
    expected={'chen':'dylan','lin':'serena'};masters={}
    for cut in cuts:
        role=cut['role']
        if role not in expected or cut['speaker']!=expected[role]:raise ValueError('Role voice changed')
        fingerprint=(cut['source'],cut['source_sha256'])
        if role in masters and masters[role]!=fingerprint:raise ValueError('Actor takes came from different voice masters')
        masters[role]=fingerprint
    if set(masters)!=set(expected):raise ValueError('Missing actor master')
