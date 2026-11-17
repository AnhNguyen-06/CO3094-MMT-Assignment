"""Deterministic in-process TCP flow-control simulation; no raw sockets/root.
Run: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 tests/flow_control_simulation.py
"""
import time, threading, struct, contextlib, io
from streaprous_socket import streaprous_raw_connection as m
m.MSS=10
class Wire:
    def __init__(self): self.drop_update=False; self.dropped=False; self.drop_data=False; self.keys=keys.copy(); self.frames=[]; self.peaks={}; self.probes=[]; self.block_updates=False
    def sendto(self,p,a):
        h=(p[0]&15)*4; src,dst,seq,ack,off,flags,win,_,_=struct.unpack('!HHLLBBHHH',p[h:h+20]); data=p[h+(off>>4)*4:]
        if len(data)>1:
            with m.connections_lock:
                sender=m.connections[self.keys[src]]
                # Retransmissions reuse old sequence space; ordinary new data
                # must fit the current byte budget before transmission.
                if seq==sender.next_seq_num:
                    budget=max(0,sender.peer_rwnd-m.seq_diff(sender.next_seq_num,sender.send_base))
                    assert len(data)<=budget, (len(data),budget)
        key=self.keys[dst]; self.frames.append((src,seq,ack,win,len(data),time.monotonic()))
        if src==11001 and len(data)==1:
            self.probes.append(time.monotonic())
            if self.block_updates and len(self.probes)==1:
                self.dropped=True; return len(p)  # lose first probe too
            self.block_updates=False
        if self.block_updates and src==11002 and not data and win>0:
            self.dropped=True; return len(p)
        if self.drop_data and src==11001 and len(data)>1 and not self.dropped:
            self.dropped=True; return len(p)
        if self.drop_update and src==11002 and not data and win>0 and not self.dropped:
            self.dropped=True; return len(p)
        m.get_packet_queue(key).put((p,a))
        if flags&16:m.get_ack_queue(key).put((p,a))
        return len(p)
def setup(cap,window=None,base=11000,clear=True):
    global keys
    if clear:m.close_all_connections()
    time.sleep(.02)
    keys={base+1:('127.0.0.2',base+2),base+2:('127.0.0.1',base+1)}
    for port,peer,ip,rip,seq,rseq in [(base+1,base+2,'127.0.0.1','127.0.0.2',100,200),(base+2,base+1,'127.0.0.2','127.0.0.1',200,100)]:
        c=m.new_connection(client_ip=rip,client_port=peer,server_ip=ip,server_port=port,state='ESTABLISHED',server_seq=seq,client_seq=rseq,expected_final_ack=0,last_activity=time.time(),rcv_buffer_size=cap,peer_rwnd=cap if window is None else window)
        m.connections[keys[port]]=c
    return m.connections[keys[base+1]],m.connections[keys[base+2]]
def run(cap,drop_update=False,drop_data=False,initial_zero=False,block_updates=False):
    a,b=setup(cap,0 if initial_zero else None); w=Wire(); w.drop_data=drop_data
    m.start_connection_receiver(w,a); m.start_connection_receiver(w,b)
    data=bytes(range(70)); result=[]
    t=threading.Thread(target=lambda:result.append(m.run_conn_send(w,a,data)));t.start()
    time.sleep(.15)
    if drop_update:w.drop_update=True
    w.block_updates=block_updates
    received=bytearray(); end=time.monotonic()+12
    while len(received)<len(data) and time.monotonic()<end:
        with m.connections_lock:
            c=m.connections[keys[11002]]; occupied=sum(map(len,c.rcv_buffer.values())); assert occupied<=cap
            available=m.seq_diff(c.client_seq,(c.last_byte_read+1)&m.M32)
        if available>0:received.extend(m.run_conn_recv(w,b,3))
        time.sleep(.02)
    t.join(3)
    assert not t.is_alive(), 'sender stalled'
    assert received==data,(len(received),result)
    assert result==[len(data)],result
    if drop_update or drop_data:assert w.dropped
    if initial_zero:
        first=[x for x in w.frames if x[0]==11001 and x[4]]; assert first[0][4]==1
    if block_updates:
        assert len(w.probes)>=2
        assert w.probes[1]-w.probes[0]>=.9, 'probe interval too short'
    m.close_all_connections(); return len(w.frames)
with contextlib.redirect_stdout(io.StringIO()):
    counts=[run(8,drop_update=True),run(40,drop_data=True),run(8,initial_zero=True),run(8,block_updates=True)]
print('PASS slow receiver/full buffer/lost window update; gap recovery; initial zero window + accepted new-byte probe; lost opening updates and lost first probe',counts)

# Two simultaneous connections: one remains blocked while the other completes.
with contextlib.redirect_stdout(io.StringIO()):
    a,b=setup(8,0); w1=Wire()
    c,d=setup(20,base=12000,clear=False); w2=Wire()
    for wire,left,right in [(w1,a,b),(w2,c,d)]:
        m.start_connection_receiver(wire,left); m.start_connection_receiver(wire,right)
    result=[]
    blocked=threading.Thread(target=lambda:result.append(m.run_conn_send(w1,a,b'blocked')))
    blocked.start()
    assert m.run_conn_send(w2,c,b'independent')==11
    assert m.run_conn_recv(w2,d)==b'independent'
    assert blocked.is_alive()
    m.close_all_connections(); blocked.join(2)
    assert not blocked.is_alive() and result==[-1]
print('PASS simultaneous connections; zero-window sender stops on close')
