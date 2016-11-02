 0                   1                   2                   3   
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        | ----\
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ ---- UDP Packet Header (8 Bytes)
|             Length            |           Checksum            | ----/
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Sequence Number        |     Acknowledgment Number     | ----\
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ -----\
|                               |    |   Data   |    |A|W|D|C|E|| ------\
|         Window Length         |x000|  Offset  |x000|C|I|T|O|N|| ------ CRP Packet Header (12 Bytes)
|                               |    |          |    |K|N|A|N|D|| ------/
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ -----/
|                           Checksum                            | ----/
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                            Payload                            |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

UDP Header Values:

Source Port:
   -  16-bit integer value in the range [0-65535] that indicates the port number associated with the source of the message

Destination Port:
   -  16-bit integer value in the range [0-65535] that indicates the port number associated with the destination of the message

Length:
   -  16-bit integer value that indicates the length, in bytes, of the UDP header and message. This has a minimum value of 8 since the UDP header is 8 bytes. With the addition of a 12 byte CRP header within a UDP message, this value will have a minimum of 20 bytes.

Checksum:
   -  16-bit checksum field used for error detection


CRP Header Values:

Sequence Number:
   -  16-bit integer value in the range [0-65535] that indicates the ordering of a packet within a data stream. This number is established in the connection initiation stage, and every subsequent packet will increment the sequence number by one. This number should be taken modulo 216 so that sequence number incremented greater than 65535 are rolled over to begin at 0.

Acknowledgement Number:
   -  16-bit integer value in the range [0-65535] that contains the value of the next sequence number the receiver is expecting. This value is checked in the case that the ACK flag is set within the packet header.

Window Length:
   -  16-bit integer value that indicates the number of bytes that the receiver is ready and able to accept. This variable can be changed, but in order to notify the sender of a change, the WIN flag must be set within the packet header.

Data Offset:
   -  5-bit integer that represents the number of bytes in the CRP header. In this implementation, the CRP header will always be a set length of 12 bytes, but this field allows the CRP header to be extended in the future with more options. This value ensures that the start of the payload data can be found.

Empty:
   -  6-bit field that will always be zeros. This acts as padding between the offset and flags so that the flags end on a 32-bit word.

Flags:
   -  5-bit field of control bits that indicate specific information when set
      o  ACK: acknowledgment bit. If this bit is set, it indicates that a packet is being acknowledged, and the next packet from the sender is indicated by the Acknowledgment Number field.
      o  WIN: window change bit. If this bit is set, it indicates that the window size had changed, and flow should be adjusted accordingly.
      o  DTA: data bit. If this bit is set, it indicates that the packet contains a data payload. This would allow for simple implementation of piggybacking, since an ACK and DTA flag being set indicates both an acknowledgment and new data from the receiver.
      o  CON: connection bit. If this bit is set, it indicates that the sender is requesting a connection, and proper sequence numbers should be established.
      o  END: end bit. If this bit is set, it indicates that the sender is ready to close the connection.

CRC32 Checksum:
   -  32-bit checksum that is calculated using a Cyclic Redundancy Check, specifically CRC32. This field is used to make sure that a packet is delivered uncorrupted.
