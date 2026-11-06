/*****************************************************************************
 * VLCHelperCode.m: generic helper code
 *****************************************************************************
 * Copyright (C) 2016 VideoLabs SAS
 * $Id$
 *
 * Authors: Felix Paul Kühne <fkuehne # videolan.org>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 2.1 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
 *****************************************************************************/

#import <VLCHelperCode.h>

NSString *toNSStr(const char *str) {
    return str != NULL ? [NSString stringWithUTF8String:str] : @"";
}

dispatch_queue_attr_t VLCQueueAttrWithQOS(dispatch_queue_attr_t attr, int qosClass)
{
    if (@available(iOS 8.0, macOS 10.10, tvOS 9.0, *))
        return dispatch_queue_attr_make_with_qos_class(attr, (dispatch_qos_class_t)qosClass, 0);
    return attr;
}
