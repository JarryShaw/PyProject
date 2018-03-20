# -*- coding: utf-8 -*-
"""reassembly IPv4 fragments

``jspcap.reassembly.ipv4`` contains ``IPv4_Reassembly``
only, which reconstructs fragmented IPv4 packets back to
origin. The algorithm for IPv4 reassembly is decribed as
below.

    FO    - Fragment Offset
    IHL   - Internet Header Length
    MF    - More Fragments flag
    TTL   - Time To Live
    NFB   - Number of Fragment Blocks
    TL    - Total Length
    TDL   - Total Data Length
    BUFID - Buffer Identifier
    RCVBT - Fragment Received Bit Table
    TLB   - Timer Lower Bound

DO {
    BUFID <- source|destination|protocol|identification;

    IF (FO = 0 AND MF = 0) {
        IF (buffer with BUFID is allocated) {
            flush all reassembly for this BUFID;
            Submit datagram to next step;
            DONE.
        }
    }

    IF (no buffer with BUFID is allocated) {
        allocate reassembly resources with BUFID;
        TIMER <- TLB;
        TDL <- 0;
        put data from fragment into data buffer with BUFID
            [from octet FO*8 to octet (TL-(IHL*4))+FO*8];
        set RCVBT bits [from FO to FO+((TL-(IHL*4)+7)/8)];
    }

    IF (MF = 0) {
        TDL <- TL-(IHL*4)+(FO*8)
    }

    IF (FO = 0) {
        put header in header buffer
    }

    IF (TDL # 0 AND all RCVBT bits [from 0 to (TDL+7)/8] are set) {
        TL <- TDL+(IHL*4)
        Submit datagram to next step;
        free all reassembly resources for this BUFID;
        DONE.
    }

    TIMER <- MAX(TIMER,TTL);

} give up until (next fragment or timer expires);

timer expires: {
    flush all reassembly with this BUFID;
    DONE.
}

"""
# Reassembly IPv4 Fragments
# Reconstruct IPv4 packets back to origin


from jspcap.reassembly.ip import IP_Reassembly


__all__ = ['IPv4_Reassembly']


class IPv4_Reassembly(IP_Reassembly):
    """Reassembly for IPv4 payload.

    Usage:
        >>> from reassembly import IPv4_Reassembly
        # Initialise instance:
        >>> ipv4_reassembly = IPv4_Reassembly()
        # Call reassembly:
        >>> ipv4_reassembly(packet_dict)
        # Fetch result:
        >>> result = ipv4_reassembly.datagram

    Keyword arguments:
        * strict -- bool, if strict set to True, all datagram will return
                    else only implemented ones will submit (False in default)
                    < True / False >

    Properties:
        * name -- str, protocol of current packet
        * count -- int, total number of reassembled packets
        * datagram -- tuple, reassembled datagram, which structure may vary
                        according to its protocol

    Methods:
        * reassembly -- perform the reassembly procedure
        * submit -- submit reassembled payload
        * fetch -- fetch datagram
        * index -- return datagram index
        * run -- run automatically

    Attributes:
        * _strflg -- bool, stirct mode flag
        * _buffer -- dict, buffer field
        * _dtgram -- tuple, reassembled datagram

    Terminology:
        * packet_dict = dict(
            bufid = tuple(
                ipv4.src,                   # source IP address
                ipv4.dst,                   # destination IP address
                ipv4.id,                    # identification
                ipv4.proto,                 # payload protocol type
            ),
            num = frame.number,             # original packet range number
            fo = ipv4.frag_offset,          # fragment offset
            ihl = ipv4.hdr_len,             # internet header length
            mf = ipv4.flags.mf,             # more fragment flag
            tl = ipv4.len,                  # total length, header includes
            header = ipv4.header,           # raw bytearray type header
            payload = ipv4.payload,         # raw bytearray type payload
        )
        * (tuple) datagram
            |--> (dict) data
            |       |--> 'NotImplemented' : (bool) True --> implemented
            |       |--> 'index' : (tuple) packet numbers
            |       |                |--> (int) original packet range number
            |       |--> 'packet' : (bytes/None) reassembled IPv4 packet
            |--> (dict) data
            |       |--> 'NotImplemented' : (bool) False --> not implemented
            |       |--> 'index' : (tuple) packet numbers
            |       |                |--> (int) original packet range number
            |       |--> 'header' : (bytes/None) IPv4 header
            |       |--> 'payload' : (tuple/None) partially reassembled IPv4 payload
            |                        |--> (bytes/None) IPv4 payload fragment
            |--> (dict) data ...
        * (dict) buffer --> memory buffer for reassembly
            |--> (tuple) BUFID : (dict)
            |       |--> ipv4.src    |
            |       |--> ipc4.dst    |
            |       |--> ipv4.id     |
            |       |--> ipv4.proto  |
            |                        |--> 'TDL' : (int) total data length
            |                        |--> RCVBT : (bytearray) fragment received bit table
            |                        |               |--> (bytes) b\x00' not received
            |                        |               |--> (bytes) b\x01' received
            |                        |               |--> (bytes) ...
            |                        |--> 'index' : (list) list of reassembled packets
            |                        |               |--> (int) packet range number
            |                        |--> 'header' : (bytearray) header buffer
            |                        |--> 'datagram' : (bytearray) data buffer, holes set to b'\x00'
            |--> (tuple) BUFID ...

    """
    ##########################################################################
    # Properties.
    ##########################################################################

    @property
    def name(self):
        """Protocol of current packet."""
        return 'Internet Protocol version 4'